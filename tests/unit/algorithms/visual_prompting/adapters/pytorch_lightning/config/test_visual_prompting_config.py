"""Tests the methods in config."""

# Copyright (C) 2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

from typing import Optional

import pytest
from omegaconf import DictConfig, OmegaConf

from otx.algorithms.visual_prompting.adapters.pytorch_lightning.config.visual_prompting_config import (
    get_visual_promtping_config,
    update_visual_prompting_config,
)
from tests.test_suite.e2e_test_system import e2e_pytest_unit


@e2e_pytest_unit
@pytest.mark.parametrize(
    "model_checkpoint,resume_from_checkpoint",
    [
        (None, None),
        ("model_checkpoint.ckpt", None),
        (None, "resume_from_checkpoint.ckpt"),
    ],
)
def test_get_visual_promtping_config(
    tmpdir, mocker, model_checkpoint: Optional[str], resume_from_checkpoint: Optional[str]
):
    """Test get_visual_promtping_config."""
    task_name = "sam_vit_b"
    mocker_otx_config = mocker.patch("otx.api.configuration.configurable_parameters.ConfigurableParameters")
    output_path = str(tmpdir.mkdir("visual_prompting_training_test"))
    config = get_visual_promtping_config(
        task_name, mocker_otx_config, output_path, model_checkpoint, resume_from_checkpoint
    )

    assert isinstance(config, DictConfig)
    assert config.get("dataset", False)
    assert config.get("model", False)
    assert config.get("optimizer", False)
    assert config.get("callback", False)
    assert config.get("trainer", False)
    assert config.get("trainer").get("resume_from_checkpoint", None) == resume_from_checkpoint
    if model_checkpoint is not None:
        assert config.get("model").get("checkpoint") == model_checkpoint


@e2e_pytest_unit
def test_update_visual_prompting_config():
    """Test update_visual_prompting_config."""
    otx_config = OmegaConf.create(
        {
            "groups": ["learning_parameters"],
            "learning_parameters": {"parameters": ["param1"], "param1": "updated_value1"},
            "parameters": [],
        }
    )
    visual_prompting_config = OmegaConf.create({"param1": "value1", "param2": "value2"})

    update_visual_prompting_config(visual_prompting_config, otx_config)

    assert visual_prompting_config["param1"] == "updated_value1"