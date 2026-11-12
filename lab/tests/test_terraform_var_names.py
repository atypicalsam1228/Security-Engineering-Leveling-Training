from labcli.context import _terraform_var_name


def test_upper_case_windows_names_become_lowercase_terraform_names() -> None:
    assert _terraform_var_name("TF_VAR_LAB_ID") == "TF_VAR_lab_id"
    assert _terraform_var_name("TF_VAR_GUARD_BUDGET_TOPIC_ARN") == "TF_VAR_guard_budget_topic_arn"


def test_already_lowercase_names_are_unchanged() -> None:
    assert _terraform_var_name("TF_VAR_region") == "TF_VAR_region"
