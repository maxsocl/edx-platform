"""
Utility methods useful for Studio page tests.
"""
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bok_choy.promise import EmptyPromise
from bok_choy.javascript import js_defined

from ...tests.helpers import disable_animations


def click_css(page, css, source_index=0, require_notification=True):
    """
    Click the button/link with the given css and index on the specified page (subclass of PageObject).

    Will only consider elements that are displayed and have a height and width greater than zero.

    If require_notification is False (default value is True), the method will return immediately.
    Otherwise, it will wait for the "mini-notification" to appear and disappear.
    """
    def _is_visible(el):
        # Only make the call to size once (instead of once for the height and once for the width)
        # because otherwise you will trigger a extra query on a remote element.
        return el.is_displayed() and all(size > 0 for size in el.size.itervalues())

    # Disable all animations for faster testing with more reliable synchronization
    disable_animations(page)
    # Click on the element in the browser
    page.q(css=css).filter(lambda el: _is_visible(el)).nth(source_index).click()

    if require_notification:
        wait_for_notification(page)

    # Some buttons trigger ajax posts
    # (e.g. .add-missing-groups-button as configured in split_test_author_view.js)
    # so after you click anything wait for the ajax call to finish
    page.wait_for_ajax()


def wait_for_notification(page):
    """
    Waits for the "mini-notification" to appear and disappear on the given page (subclass of PageObject).
    """
    def _is_saving():
        return page.q(css='.wrapper-notification-mini.is-shown').present

    def _is_saving_done():
        return page.q(css='.wrapper-notification-mini.is-hiding').present

    EmptyPromise(_is_saving, 'Notification should have been shown.', timeout=60).fulfill()
    EmptyPromise(_is_saving_done, 'Notification should have been hidden.', timeout=60).fulfill()


@js_defined('window.jQuery')
def press_the_notification_button(page, name):
    # Because the notification uses a CSS transition,
    # Selenium will always report it as being visible.
    # This makes it very difficult to successfully click
    # the "Save" button at the UI level.
    # Instead, we use JavaScript to reliably click
    # the button.
    btn_css = 'div#page-notification button.action-%s' % name.lower()
    page.browser.execute_script("$('{}').focus().click()".format(btn_css))
    page.wait_for_ajax()


def add_discussion(page, menu_index=0):
    """
    Add a new instance of the discussion category.

    menu_index specifies which instance of the menus should be used (based on vertical
    placement within the page).
    """
    page.wait_for_component_menu()
    click_css(page, 'button>span.large-discussion-icon', menu_index)


def add_advanced_component(page, menu_index, name):
    """
    Adds an instance of the advanced component with the specified name.

    menu_index specifies which instance of the menus should be used (based on vertical
    placement within the page).
    """
    # Click on the Advanced icon.
    page.wait_for_component_menu()
    click_css(page, 'button>span.large-advanced-icon', menu_index, require_notification=False)

    # This does an animation to hide the first level of buttons
    # and instead show the Advanced buttons that are available.
    # We should be OK though because click_css turns off jQuery animations

    # Make sure that the menu of advanced components is visible before clicking (the HTML is always on the
    # page, but will have display none until the large-advanced-icon is clicked).
    page.wait_for_element_visibility('.new-component-advanced', 'Advanced component menu is visible')

    # Now click on the component to add it.
    component_css = 'button[data-category={}]'.format(name)
    page.wait_for_element_visibility(component_css, 'Advanced component {} is visible'.format(name))

    # Adding some components, e.g. the Discussion component, will make an ajax call
    # but we should be OK because the click_css method is written to handle that.
    click_css(page, component_css, 0)


def add_component(page, item_type, specific_type):
    """
    Click one of the "Add New Component" buttons.

    item_type should be "advanced", "html", "problem", or "video"

    specific_type is required for some types and should be something like
    "Blank Common Problem".
    """
    btn = page.q(css='.add-xblock-component .add-xblock-component-button[data-type={}]'.format(item_type))
    multiple_templates = btn.filter(lambda el: 'multiple-templates' in el.get_attribute('class')).present
    btn.click()
    if multiple_templates:
        sub_template_menu_div_selector = '.new-component-{}'.format(item_type)
        page.wait_for_element_visibility(sub_template_menu_div_selector, 'Wait for the templates sub-menu to appear')
        page.wait_for_element_invisibility(
            '.add-xblock-component .new-component',
            'Wait for the add component menu to disappear'
        )

        all_options = page.q(css='.new-component-{} ul.new-component-template li button span'.format(item_type))
        chosen_option = all_options.filter(lambda el: el.text == specific_type).first
        chosen_option.click()
    wait_for_notification(page)
    page.wait_for_ajax()


def add_html_component(page, menu_index, boilerplate=None):
    """
    Adds an instance of the HTML component with the specified name.

    menu_index specifies which instance of the menus should be used (based on vertical
    placement within the page).
    """
    # Click on the HTML icon.
    page.wait_for_component_menu()
    click_css(page, 'button>span.large-html-icon', menu_index, require_notification=False)

    # Make sure that the menu of HTML components is visible before clicking
    page.wait_for_element_visibility('.new-component-html', 'HTML component menu is visible')

    # Now click on the component to add it.
    component_css = 'button[data-category=html]'
    if boilerplate:
        component_css += '[data-boilerplate={}]'.format(boilerplate)
    else:
        component_css += ':not([data-boilerplate])'

    page.wait_for_element_visibility(component_css, 'HTML component {} is visible'.format(boilerplate))

    # Adding some components will make an ajax call but we should be OK because
    # the click_css method is written to handle that.
    click_css(page, component_css, 0)


@js_defined('window.jQuery')
def type_in_codemirror(page, index, text, find_prefix="$"):
    script = """
    var cm = {find_prefix}('div.CodeMirror:eq({index})').get(0).CodeMirror;
    CodeMirror.signal(cm, "focus", cm);
    cm.setValue(arguments[0]);
    CodeMirror.signal(cm, "blur", cm);""".format(index=index, find_prefix=find_prefix)
    page.browser.execute_script(script, str(text))


@js_defined('window.jQuery')
def get_codemirror_value(page, index=0, find_prefix="$"):
    return page.browser.execute_script(
        """
        return {find_prefix}('div.CodeMirror:eq({index})').get(0).CodeMirror.getValue();
        """.format(index=index, find_prefix=find_prefix)
    )


def confirm_prompt(page, cancel=False, require_notification=None):
    """
    Ensures that a modal prompt and confirmation button are visible, then clicks the button. The prompt is canceled iff
    cancel is True.
    """
    page.wait_for_element_visibility('.prompt', 'Prompt is visible')
    confirmation_button_css = '.prompt .action-' + ('secondary' if cancel else 'primary')
    page.wait_for_element_visibility(confirmation_button_css, 'Confirmation button is visible')
    require_notification = (not cancel) if require_notification is None else require_notification
    click_css(page, confirmation_button_css, require_notification=require_notification)


def set_input_value(page, css, value):
    """
    Sets the text field with the given label (display name) to the specified value.
    """
    input_element = page.q(css=css).results[0]
    # Click in the input to give it the focus
    input_element.click()
    # Select all, then input the value
    input_element.send_keys(Keys.CONTROL + 'a')
    input_element.send_keys(value)
    # Return the input_element for chaining
    return input_element


def set_input_value_and_save(page, css, value):
    """
    Sets the text field with given label (display name) to the specified value, and presses Save.
    """
    set_input_value(page, css, value).send_keys(Keys.ENTER)
    page.wait_for_ajax()


def drag(page, source_index, target_index, placeholder_height=0):
    """
    Gets the drag handle with index source_index (relative to the vertical layout of the page)
    and drags it to the location of the drag handle with target_index.

    This should drag the element with the source_index drag handle BEFORE the
    one with the target_index drag handle.
    """
    draggables = page.q(css='.drag-handle')
    source = draggables[source_index]
    target = draggables[target_index]
    action = ActionChains(page.browser)
    action.click_and_hold(source).move_to_element_with_offset(
        target, 0, placeholder_height
    )
    if placeholder_height == 0:
        action.release(target).perform()
    else:
        action.release().perform()
    wait_for_notification(page)


def verify_ordering(test_class, page, expected_orderings):
    """
    Verifies the expected ordering of xblocks on the page.
    """
    xblocks = page.xblocks
    blocks_checked = set()
    for expected_ordering in expected_orderings:
        for xblock in xblocks:
            parent = expected_ordering.keys()[0]
            if xblock.name == parent:
                blocks_checked.add(parent)
                children = xblock.children
                expected_length = len(expected_ordering.get(parent))
                test_class.assertEqual(
                    expected_length, len(children),
                    "Number of children incorrect for group {0}. Expected {1} but got {2}.".format(parent, expected_length, len(children)))
                for idx, expected in enumerate(expected_ordering.get(parent)):
                    test_class.assertEqual(expected, children[idx].name)
                    blocks_checked.add(expected)
                break
    test_class.assertEqual(len(blocks_checked), len(xblocks))
