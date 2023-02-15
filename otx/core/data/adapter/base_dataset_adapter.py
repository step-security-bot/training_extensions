"""Base Class for Dataset Adapter."""

# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

# pylint: disable=invalid-name, too-many-locals, no-member, too-many-instance-attributes, unused-argument

import abc
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Union

import datumaro
from datumaro.components.annotation import Annotation as DatumaroAnnotation
from datumaro.components.annotation import AnnotationType as DatumaroAnnotationType
from datumaro.components.annotation import Categories as DatumaroCategories
from datumaro.components.dataset import Dataset as DatumaroDataset

from otx.api.entities.annotation import (
    Annotation,
    AnnotationSceneEntity,
    AnnotationSceneKind,
    NullAnnotationSceneEntity,
)
from otx.api.entities.datasets import DatasetEntity
from otx.api.entities.id import ID
from otx.api.entities.label import LabelEntity
from otx.api.entities.label_schema import LabelGroup, LabelGroupType, LabelSchemaEntity
from otx.api.entities.model_template import TaskType
from otx.api.entities.scored_label import ScoredLabel
from otx.api.entities.shapes.polygon import Point, Polygon
from otx.api.entities.shapes.rectangle import Rectangle
from otx.api.entities.subset import Subset


class BaseDatasetAdapter(metaclass=abc.ABCMeta):
    """Base dataset adapter for all of downstream tasks to use Datumaro.

    Mainly, BaseDatasetAdapter detect and import the dataset by using the function implemented in Datumaro.
    And it could prepare common variable, function (EmptyLabelSchema, LabelSchema, ..) commonly consumed under all tasks

    Args:
        task_type [TaskType]: type of the task
        train_data_roots (Optional[str]): Path for training data
        val_data_roots (Optional[str]): Path for validation data
        test_data_roots (Optional[str]): Path for test data
        unlabeled_data_roots (Optional[str]): Path for unlabeled data

    Since all adapters can be used for training and validation,
    the default value of train/val/test_data_roots was set to None.

    i.e)
    For the training/validation phase, test_data_roots is not used.
    For the test phase, train_data_roots and val_data_root are not used.
    """

    def __init__(
        self,
        task_type: TaskType,
        train_data_roots: Optional[str] = None,
        val_data_roots: Optional[str] = None,
        test_data_roots: Optional[str] = None,
        unlabeled_data_roots: Optional[str] = None,
    ):
        self.task_type = task_type
        self.domain = task_type.domain
        self.data_type: str
        self.is_train_phase: bool

        self.dataset = self._import_dataset(
            train_data_roots=train_data_roots,
            val_data_roots=val_data_roots,
            test_data_roots=test_data_roots,
            unlabeled_data_roots=unlabeled_data_roots,
        )

        self.category_items: Dict[DatumaroAnnotationType, DatumaroCategories]
        self.label_groups: List[str]
        self.label_entities: List[LabelEntity]
        self.label_schema: LabelSchemaEntity

    def _import_dataset(
        self,
        train_data_roots: Optional[str] = None,
        val_data_roots: Optional[str] = None,
        test_data_roots: Optional[str] = None,
        unlabeled_data_roots: Optional[str] = None,
    ) -> Dict[Subset, DatumaroDataset]:
        """Import dataset by using Datumaro.import_from() method.

        Args:
            train_data_roots (Optional[str]): Path for training data
            val_data_roots (Optional[str]): Path for validation data
            test_data_roots (Optional[str]): Path for test data
            unlabeled_data_roots (Optional[str]): Path for unlabeled data

        Returns:
            DatumaroDataset: Datumaro Dataset
        """
        dataset = {}
        if train_data_roots is None and test_data_roots is None:
            raise ValueError("At least 1 data_root is needed to train/test.")

        # Construct dataset for training, validation, testing, unlabeled
        if train_data_roots:
            # Find self.data_type and task_type
            data_type_candidates = self._detect_dataset_format(path=train_data_roots)
            self.data_type = self._select_data_type(data_type_candidates)

            datumaro_dataset = DatumaroDataset.import_from(train_data_roots, format=self.data_type)

            # Prepare subsets by using Datumaro dataset
            for k, v in datumaro_dataset.subsets().items():
                if "train" in k or "default" in k:
                    dataset[Subset.TRAINING] = v
                elif "val" in k:
                    dataset[Subset.VALIDATION] = v
            self.is_train_phase = True

            # If validation is manually defined --> set the validation data according to user's input
            if val_data_roots:
                val_data_candidates = self._detect_dataset_format(path=val_data_roots)
                val_data_type = self._select_data_type(val_data_candidates)
                dataset[Subset.VALIDATION] = DatumaroDataset.import_from(val_data_roots, format=val_data_type)

        if test_data_roots:
            test_data_candidates = self._detect_dataset_format(path=test_data_roots)
            test_data_type = self._select_data_type(test_data_candidates)
            dataset[Subset.TESTING] = DatumaroDataset.import_from(test_data_roots, format=test_data_type)
            self.is_train_phase = False

        if unlabeled_data_roots is not None:
            dataset[Subset.UNLABELED] = DatumaroDataset.import_from(unlabeled_data_roots, format="image_dir")

        return dataset

    @abstractmethod
    def get_otx_dataset(self) -> DatasetEntity:
        """Get DatasetEntity."""
        raise NotImplementedError

    def get_label_schema(self) -> LabelSchemaEntity:
        """Get Label Schema."""
        return self._generate_default_label_schema(self.label_entities)

    def _detect_dataset_format(self, path: str) -> str:
        """Detect dataset format (ImageNet, COCO, ...)."""
        return datumaro.Environment().detect_dataset(path=path)

    def _generate_empty_label_entity(self) -> LabelGroup:
        """Generate Empty Label Group for H-label, Multi-label Classification."""
        empty_label = LabelEntity(name="Empty label", is_empty=True, domain=self.domain)
        empty_group = LabelGroup(name="empty", labels=[empty_label], group_type=LabelGroupType.EMPTY_LABEL)
        return empty_group

    def _generate_default_label_schema(self, label_entities: List[LabelEntity]) -> LabelSchemaEntity:
        """Generate Default Label Schema for Multi-class Classification, Detecion, Etc."""
        label_schema = LabelSchemaEntity()
        main_group = LabelGroup(
            name="labels",
            labels=label_entities,
            group_type=LabelGroupType.EXCLUSIVE,
        )
        label_schema.add_group(main_group)
        return label_schema

    def _prepare_label_information(
        self,
        datumaro_dataset: Dict[Subset, DatumaroDataset],
    ) -> Dict[str, Any]:
        # Get datumaro category information
        if self.is_train_phase:
            label_categories_list = (
                datumaro_dataset[Subset.TRAINING].categories().get(DatumaroAnnotationType.label, None)
            )
        else:
            label_categories_list = (
                datumaro_dataset[Subset.TESTING].categories().get(DatumaroAnnotationType.label, None)
            )
        category_items = label_categories_list.items
        label_groups = label_categories_list.label_groups

        # LabelEntities
        label_entities = [
            LabelEntity(name=class_name.name, domain=self.domain, is_empty=False, id=ID(i))
            for i, class_name in enumerate(category_items)
        ]

        return {"category_items": category_items, "label_groups": label_groups, "label_entities": label_entities}

    def _select_data_type(self, data_candidates: Union[List[str], str]) -> str:
        """Select specific type among candidates.

        Args:
            data_candidates (Union[List[str], str]): Type candidates made by Datumaro.Environment().detect_dataset()

        Returns:
            str: Selected data type
        """
        return data_candidates[0]

    def _get_ann_scene_entity(self, shapes: List[Annotation]) -> AnnotationSceneEntity:
        annotation_scene: Optional[AnnotationSceneEntity] = None
        if len(shapes) == 0:
            annotation_scene = NullAnnotationSceneEntity()
        else:
            annotation_scene = AnnotationSceneEntity(kind=AnnotationSceneKind.ANNOTATION, annotations=shapes)
        return annotation_scene

    def _get_label_entity(self, annotation: DatumaroAnnotation) -> Annotation:
        """Get label entity."""
        return Annotation(
            Rectangle.generate_full_box(), labels=[ScoredLabel(label=self.label_entities[annotation.label])]
        )

    def _get_normalized_bbox_entity(self, annotation: DatumaroAnnotation, width: int, height: int) -> Annotation:
        """Get bbox entity w/ normalization."""
        return Annotation(
            Rectangle(
                x1=annotation.points[0] / width,
                y1=annotation.points[1] / height,
                x2=annotation.points[2] / width,
                y2=annotation.points[3] / height,
            ),
            labels=[ScoredLabel(label=self.label_entities[annotation.label])],
        )

    def _get_original_bbox_entity(self, annotation: DatumaroAnnotation) -> Annotation:
        """Get bbox entity w/o normalization."""
        return Annotation(
            Rectangle(
                x1=annotation.points[0],
                y1=annotation.points[1],
                x2=annotation.points[2],
                y2=annotation.points[3],
            ),
            labels=[ScoredLabel(label=self.label_entities[annotation.label])],
        )

    def _get_polygon_entity(self, annotation: DatumaroAnnotation, width: int, height: int) -> Annotation:
        """Get polygon entity."""
        return Annotation(
            Polygon(
                points=[
                    Point(x=annotation.points[i] / width, y=annotation.points[i + 1] / height)
                    for i in range(0, len(annotation.points), 2)
                ]
            ),
            labels=[ScoredLabel(label=self.label_entities[annotation.label])],
        )

    def remove_unused_label_entities(self, used_labels: List):
        """Remove unused label from label entities.

        Because label entities will be used to make Label Schema,
        If there is unused label in Label Schema, it will hurts the model performance.
        So, remove the unused label from label entities.

        Args:
            used_labels (List): list for index of used label
        """
        clean_label_entities = []
        for used_label in used_labels:
            clean_label_entities.append(self.label_entities[used_label])
        self.label_entities = clean_label_entities