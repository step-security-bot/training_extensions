"""Tests for Semantic segmentation with OTX CLI"""
# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import os

import pytest
import torch

from otx.api.entities.model_template import parse_model_template
from tests.test_suite.e2e_test_system import e2e_pytest_component
from tests.test_suite.run_test_command import (
    get_template_dir,
    nncf_optimize_testing,
    otx_deploy_openvino_testing,
    otx_eval_deployment_testing,
    otx_eval_openvino_testing,
    otx_eval_testing,
    otx_export_testing,
    otx_hpo_testing,
    otx_resume_testing,
    otx_train_testing,
)

args = {
    "--train-data-roots": "tests/assets/common_semantic_segmentation_dataset/train",
    "--val-data-roots": "tests/assets/common_semantic_segmentation_dataset/val",
    "--test-data-roots": "tests/assets/common_semantic_segmentation_dataset/val",
    "--input": "tests/assets/common_semantic_segmentation_dataset/train/images",
    "train_params": [
        "params",
        "--learning_parameters.learning_rate_fixed_iters",
        "0",
        "--learning_parameters.learning_rate_warmup_iters",
        "1",
        "--learning_parameters.num_iters",
        "1",
        "--learning_parameters.batch_size",
        "4",
    ],
}

args_semisl = {
    "--train-data-roots": "tests/assets/common_semantic_segmentation_dataset/train",
    "--val-data-roots": "tests/assets/common_semantic_segmentation_dataset/val",
    "--test-data-roots": "tests/assets/common_semantic_segmentation_dataset/val",
    "--unlabeled-data-roots": "tests/assets/common_semantic_segmentation_dataset/train",
    "train_params": [
        "params",
        "--learning_parameters.num_iters",
        "1",
        "--learning_parameters.batch_size",
        "4",
        "--algo_backend.train_type",
        "SEMISUPERVISED",
    ],
}

args_selfsl = {
    "--train-data-roots": "tests/assets/common_semantic_segmentation_dataset/train",
    "--input": "tests/assets/segmentation/custom/images/training",
    "train_params": [
        "params",
        "--learning_parameters.num_iters",
        "1",
        "--learning_parameters.batch_size",
        "4",
        "--algo_backend.train_type",
        "SELFSUPERVISED",
    ],
}

# Training params for resume, num_iters*2
resume_params = [
    "params",
    "--learning_parameters.num_iters",
    "2",
    "--learning_parameters.batch_size",
    "4",
]

otx_dir = os.getcwd()

MULTI_GPU_UNAVAILABLE = torch.cuda.device_count() <= 1
default_template = parse_model_template(
    os.path.join("otx/algorithms/segmentation/configs", "ocr_lite_hrnet_18_mod2", "template.yaml")
)
templates = [default_template]
templates_ids = [default_template.model_template_id]


class TestSegmentationCLI:
    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_train_supcon(self, template, tmp_dir_path):
        args1 = copy.deepcopy(args)
        args1["train_params"].extend(["--learning_parameters.enable_supcon", "True"])
        otx_train_testing(template, tmp_dir_path, otx_dir, args1)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_train(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        otx_train_testing(template, tmp_dir_path, otx_dir, args)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_resume(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation/test_resume"
        otx_resume_testing(template, tmp_dir_path, otx_dir, args)
        template_work_dir = get_template_dir(template, tmp_dir_path)
        args1 = copy.deepcopy(args)
        args1["train_params"] = resume_params
        args1["--resume-from"] = f"{template_work_dir}/trained_for_resume_{template.model_template_id}/weights.pth"
        otx_resume_testing(template, tmp_dir_path, otx_dir, args1)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_export(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        otx_export_testing(template, tmp_dir_path)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_eval(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        otx_eval_testing(template, tmp_dir_path, otx_dir, args)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_eval_openvino(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        otx_eval_openvino_testing(template, tmp_dir_path, otx_dir, args, threshold=1.0)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_deploy_openvino(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        otx_deploy_openvino_testing(template, tmp_dir_path, otx_dir, args)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_eval_deployment(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        otx_eval_deployment_testing(template, tmp_dir_path, otx_dir, args, threshold=1.0)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_hpo(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation/test_hpo"
        otx_hpo_testing(template, tmp_dir_path, otx_dir, args)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_nncf_optimize(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation"
        if template.entrypoints.nncf is None:
            pytest.skip("nncf entrypoint is none")

        nncf_optimize_testing(template, tmp_dir_path, otx_dir, args)

    @e2e_pytest_component
    @pytest.mark.skip(reason="CVS-101246 Multi-GPU tests are stuck while CI is running")
    @pytest.mark.skipif(MULTI_GPU_UNAVAILABLE, reason="The number of gpu is insufficient")
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_multi_gpu_train(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation/test_multi_gpu"
        args1 = copy.deepcopy(args)
        args1["--gpus"] = "0,1"
        otx_train_testing(template, tmp_dir_path, otx_dir, args1)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_train_semisl(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation/test_semisl"
        otx_train_testing(template, tmp_dir_path, otx_dir, args_semisl)

    @e2e_pytest_component
    @pytest.mark.parametrize("template", templates, ids=templates_ids)
    def test_otx_train_selfsl(self, template, tmp_dir_path):
        tmp_dir_path = tmp_dir_path / "segmentation/test_selfsl"
        otx_train_testing(template, tmp_dir_path, otx_dir, args_selfsl)