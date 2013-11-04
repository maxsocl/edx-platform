# disable missing docstring
#pylint: disable=C0111

import json
from lettuce import world, step
from nose.tools import assert_equal, assert_true  # pylint: disable=E0611
from common import type_in_codemirror, open_new_course
from advanced_settings import change_value
from course_import import import_file, go_to_import
from selenium.webdriver.common.keys import Keys

DISPLAY_NAME = "Display Name"
MAXIMUM_ATTEMPTS = "Maximum Attempts"
PROBLEM_WEIGHT = "Problem Weight"
RANDOMIZATION = 'Randomization'
SHOW_ANSWER = "Show Answer"


@step('I have created a Blank Common Problem$')
def i_created_blank_common_problem(step):
    world.create_course_with_unit()
    world.create_component_instance(
        step=step,
        category='problem',
        component_type='Blank Common Problem'
    )


@step('I edit and select Settings$')
def i_edit_and_select_settings(_step):
    world.edit_component_and_select_settings()


@step('I see the advanced settings and their expected values$')
def i_see_advanced_settings_with_values(step):
    world.verify_all_setting_entries(
        [
            [DISPLAY_NAME, "Blank Common Problem", True],
            [MAXIMUM_ATTEMPTS, "", False],
            [PROBLEM_WEIGHT, "", False],
            [RANDOMIZATION, "Never", False],
            [SHOW_ANSWER, "Finished", False],
        ])


@step('I can modify the display name')
def i_can_modify_the_display_name(_step):
    # Verifying that the display name can be a string containing a floating point value
    # (to confirm that we don't throw an error because it is of the wrong type).
    index = world.get_setting_entry_index(DISPLAY_NAME)
    set_field_value(index, '3.4')
    verify_modified_display_name()


@step('my display name change is persisted on save')
def my_display_name_change_is_persisted_on_save(step):
    world.save_component_and_reopen(step)
    verify_modified_display_name()


@step('I can specify special characters in the display name')
def i_can_modify_the_display_name_with_special_chars(_step):
    index = world.get_setting_entry_index(DISPLAY_NAME)
    set_field_value(index, "updated ' \" &")
    verify_modified_display_name_with_special_chars()


@step('my special characters and persisted on save')
def special_chars_persisted_on_save(step):
    world.save_component_and_reopen(step)
    verify_modified_display_name_with_special_chars()


@step('I can revert the display name to unset')
def can_revert_display_name_to_unset(_step):
    world.revert_setting_entry(DISPLAY_NAME)
    verify_unset_display_name()


@step('my display name is unset on save')
def my_display_name_is_persisted_on_save(step):
    world.save_component_and_reopen(step)
    verify_unset_display_name()


@step('I can select Per Student for Randomization')
def i_can_select_per_student_for_randomization(_step):
    world.browser.select(RANDOMIZATION, "Per Student")
    verify_modified_randomization()


@step('my change to randomization is persisted')
def my_change_to_randomization_is_persisted(step):
    world.save_component_and_reopen(step)
    verify_modified_randomization()


@step('I can revert to the default value for randomization')
def i_can_revert_to_default_for_randomization(step):
    world.revert_setting_entry(RANDOMIZATION)
    world.save_component_and_reopen(step)
    world.verify_setting_entry(world.get_setting_entry(RANDOMIZATION), RANDOMIZATION, "Never", False)


@step('I can set the weight to "(.*)"?')
def i_can_set_weight(_step, weight):
    set_weight(weight)
    verify_modified_weight()


@step('my change to weight is persisted')
def my_change_to_weight_is_persisted(step):
    world.save_component_and_reopen(step)
    verify_modified_weight()


@step('I can revert to the default value of unset for weight')
def i_can_revert_to_default_for_unset_weight(step):
    world.revert_setting_entry(PROBLEM_WEIGHT)
    world.save_component_and_reopen(step)
    world.verify_setting_entry(world.get_setting_entry(PROBLEM_WEIGHT), PROBLEM_WEIGHT, "", False)


@step('if I set the weight to "(.*)", it remains unset')
def set_the_weight_to_abc(step, bad_weight):
    set_weight(bad_weight)
    # We show the clear button immediately on type, hence the "True" here.
    world.verify_setting_entry(world.get_setting_entry(PROBLEM_WEIGHT), PROBLEM_WEIGHT, "", True)
    world.save_component_and_reopen(step)
    # But no change was actually ever sent to the model, so on reopen, explicitly_set is False
    world.verify_setting_entry(world.get_setting_entry(PROBLEM_WEIGHT), PROBLEM_WEIGHT, "", False)


@step('if I set the max attempts to "(.*)", it will persist as a valid integer$')
def set_the_max_attempts(step, max_attempts_set):
    # on firefox with selenium, the behaviour is different.
    # eg 2.34 displays as 2.34 and is persisted as 2
    index = world.get_setting_entry_index(MAXIMUM_ATTEMPTS)
    set_field_value(index, max_attempts_set)
    world.save_component_and_reopen(step)
    value = world.css_value('input.setting-input', index=index)
    assert value != "", "max attempts is blank"
    assert int(value) >= 0


@step('Edit High Level Source is not visible')
def edit_high_level_source_not_visible(step):
    verify_high_level_source_links(step, False)


@step('Edit High Level Source is visible')
def edit_high_level_source_links_visible(step):
    verify_high_level_source_links(step, True)


@step('If I press Cancel my changes are not persisted')
def cancel_does_not_save_changes(step):
    world.cancel_component(step)
    step.given("I edit and select Settings")
    step.given("I see the advanced settings and their expected values")


@step('I have enabled latex compiler')
def enable_latex_compiler(step):
    url = world.browser.url
    step.given("I select the Advanced Settings")
    change_value(step, 'use_latex_compiler', True)
    world.visit(url)
    world.wait_for_xmodule()


@step('I have created a LaTeX Problem')
def create_latex_problem(step):
    world.create_course_with_unit()
    step.given('I have enabled latex compiler')
    world.create_component_instance(
        step=step,
        category='problem',
        component_type='Problem Written in LaTeX',
        is_advanced=True
    )


@step('I edit and compile the High Level Source')
def edit_latex_source(_step):
    open_high_level_source()
    type_in_codemirror(1, "hi")
    world.css_click('.hls-compile')


@step('my change to the High Level Source is persisted')
def high_level_source_persisted(_step):
    def verify_text(driver):
        css_sel = '.problem div>span'
        return world.css_text(css_sel) == 'hi'

    world.wait_for(verify_text, timeout=10)


@step('I view the High Level Source I see my changes')
def high_level_source_in_editor(_step):
    open_high_level_source()
    assert_equal('hi', world.css_value('.source-edit-box'))


@step(u'I have an empty course')
def i_have_empty_course(step):
    open_new_course()


@step(u'I go to the import page')
def i_go_to_import(_step):
    go_to_import()


@step(u'I import the file "([^"]*)"$')
def i_import_the_file(_step, filename):
    import_file(filename)


@step(u'I click on "edit a draft"$')
def i_edit_a_draft(_step):
    world.css_click("a.create-draft")


@step(u'I go to the vertical "([^"]*)"$')
def i_go_to_vertical(_step, vertical):
    world.css_click("span:contains('{0}')".format(vertical))


@step(u'I go to the unit "([^"]*)"$')
def i_go_to_unit(_step, unit):
    loc = "window.location = $(\"span:contains('{0}')\").closest('a').attr('href')".format(unit)
    world.browser.execute_script(loc)


@step(u'I see a message that says "([^"]*)"$')
def i_can_see_message(_step, msg):
    msg = json.dumps(msg)     # escape quotes
    world.css_has_text("h2.title", msg)


@step(u'I can edit the problem$')
def i_can_edit_problem(_step):
    world.edit_component()


def verify_high_level_source_links(step, visible):
    if visible:
        assert_true(world.is_css_present('.launch-latex-compiler'),
                    msg="Expected to find the latex button but it is not present.")
    else:
        assert_true(world.is_css_not_present('.launch-latex-compiler'),
                    msg="Expected not to find the latex button but it is present.")

    world.cancel_component(step)
    if visible:
        assert_true(world.is_css_present('.upload-button'),
                    msg="Expected to find the upload button but it is not present.")
    else:
        assert_true(world.is_css_not_present('.upload-button'),
                    msg="Expected not to find the upload button but it is present.")


def verify_modified_weight():
    world.verify_setting_entry(world.get_setting_entry(PROBLEM_WEIGHT), PROBLEM_WEIGHT, "3.5", True)


def verify_modified_randomization():
    world.verify_setting_entry(world.get_setting_entry(RANDOMIZATION), RANDOMIZATION, "Per Student", True)


def verify_modified_display_name():
    world.verify_setting_entry(world.get_setting_entry(DISPLAY_NAME), DISPLAY_NAME, '3.4', True)


def verify_modified_display_name_with_special_chars():
    world.verify_setting_entry(world.get_setting_entry(DISPLAY_NAME), DISPLAY_NAME, "updated ' \" &", True)


def verify_unset_display_name():
    world.verify_setting_entry(world.get_setting_entry(DISPLAY_NAME), DISPLAY_NAME, 'Blank Advanced Problem', False)


def set_field_value(index, value):
    """
    Set the field to the specified value.

    Note: we cannot use css_fill here because the value is not set
    until after you move away from that field.
    Instead we will find the element, set its value, then hit the Tab key
    to get to the next field.
    """
    elem = world.css_find('div.wrapper-comp-setting input.setting-input')[index]
    elem.value = value
    elem.type(Keys.TAB)


def set_weight(weight):
    index = world.get_setting_entry_index(PROBLEM_WEIGHT)
    set_field_value(index, weight)


def open_high_level_source():
    world.css_click('a.edit-button')
    world.css_click('.launch-latex-compiler > a')
