import main
import prompts


def test_detects_backend_from_python_paths():
    diff = '+++ b/auto_pr/thing.py\n+++ b/tests/test_thing.py\n'
    assert main.detect_profiles(diff) == ['backend']


def test_detects_frontend_from_tsx_and_styles():
    diff = '+++ b/src/App.tsx\n+++ b/src/app.scss\n'
    assert main.detect_profiles(diff) == ['frontend']


def test_full_stack_diff_detects_both():
    diff = '+++ b/api/views.py\n+++ b/web/src/App.tsx\n'
    assert main.detect_profiles(diff) == ['backend', 'frontend']


def test_detects_cpp_from_sources_and_headers():
    diff = '+++ b/src/mesh_split.cpp\n+++ b/include/part.hpp\n'
    assert main.detect_profiles(diff) == ['cpp']


def test_detects_cpp_from_cuda_sources():
    assert main.detect_profiles('+++ b/kernels/anneal.cu\n') == ['cpp']


def test_docs_only_diff_detects_nothing():
    diff = '+++ b/README.md\n+++ b/docs/plan.md\n'
    assert main.detect_profiles(diff) == []


def test_extensionless_file_detects_nothing():
    assert main.detect_profiles('+++ b/Makefile\n') == []


def test_removed_file_header_is_not_treated_as_a_change():
    # Only the '+++ b/' side names the post-change path.
    diff = '--- a/legacy/old.py\n+++ /dev/null\n'
    assert main.detect_profiles(diff) == []


def test_base_prompt_used_alone_when_no_profile_matches():
    assert main.build_system_prompt([]) == prompts.BASE


def test_profile_sections_are_appended_to_the_base():
    composed = main.build_system_prompt(['backend'])
    assert composed.startswith(prompts.BASE)
    assert prompts.BACKEND in composed
    assert prompts.FRONTEND not in composed


def test_both_sections_present_for_a_full_stack_review():
    composed = main.build_system_prompt(['backend', 'frontend'])
    assert prompts.BACKEND in composed
    assert prompts.FRONTEND in composed


def test_every_profile_has_a_section():
    assert set(prompts.PROFILE_BY_EXTENSION) == set(prompts.SECTIONS)


def test_no_extension_is_claimed_by_two_profiles():
    seen = set()
    for extensions in prompts.PROFILE_BY_EXTENSION.values():
        assert not seen & extensions
        seen |= extensions
