"""
Acceptance tests for Library Content in LMS
"""
import ddt
from .base_studio_test import StudioLibraryTest, ContainerBase
from ...pages.studio.library import StudioLibraryContentXBlockEditModal, StudioLibraryContainerXBlockWrapper
from ...fixtures.course import XBlockFixtureDesc

SECTION_NAME = 'Test Section'
SUBSECTION_NAME = 'Test Subsection'
UNIT_NAME = 'Test Unit'


@ddt.ddt
class StudioLibraryContainerTest(ContainerBase, StudioLibraryTest):
    """
    Test Library Content block in LMS
    """
    def setUp(self):
        """
        Install library with some content and a course using fixtures
        """
        super(StudioLibraryContainerTest, self).setUp()
        self.outline.visit()
        subsection = self.outline.section(SECTION_NAME).subsection(SUBSECTION_NAME)
        self.unit_page = subsection.toggle_expand().unit(UNIT_NAME).go_to()

    def populate_library_fixture(self, library_fixture):
        """
        Populate the children of the test course fixture.
        """
        library_fixture.add_children(
            XBlockFixtureDesc("html", "Html1"),
            XBlockFixtureDesc("html", "Html2"),
            XBlockFixtureDesc("html", "Html3"),
        )

    def populate_course_fixture(self, course_fixture):
        """ Install a course with sections/problems, tabs, updates, and handouts """
        library_content_metadata = {
            'source_libraries': [self.library_key],
            'mode': 'random',
            'max_count': 1,
            'has_score': False
        }

        course_fixture.add_children(
            XBlockFixtureDesc('chapter', SECTION_NAME).add_children(
                XBlockFixtureDesc('sequential', SUBSECTION_NAME).add_children(
                    XBlockFixtureDesc('vertical', UNIT_NAME).add_children(
                        XBlockFixtureDesc('library_content', "Library Content", metadata=library_content_metadata)
                    )
                )
            )
        )

    def _get_library_xblock_wrapper(self, xblock):
        """
        Wraps xblock into :class:`...pages.studio.library.StudioLibraryContainerXBlockWrapper`
        """
        return StudioLibraryContainerXBlockWrapper.from_xblock_wrapper(xblock)

    @ddt.data(
        ('library-v1:111+111', 1, True),
        ('library-v1:edX+L104', 2, False),
        ('library-v1:OtherX+IDDQD', 3, True),
    )
    @ddt.unpack
    def test_can_edit_metadata(self, library_key, max_count, scored):
        """
        Scenario: Given I have a library, a course and library content xblock in a course
        When I go to studio unit page for library content block
        And I edit library content metadata and save it
        Then I can ensure that data is persisted
        """
        library_container = self._get_library_xblock_wrapper(self.unit_page.xblocks[0])
        edit_modal = StudioLibraryContentXBlockEditModal(library_container.edit())
        edit_modal.library_key = library_key
        edit_modal.count = max_count
        edit_modal.scored = scored

        library_container.save_settings()  # saving settings

        # open edit window again to verify changes are persistent
        edit_modal = StudioLibraryContentXBlockEditModal(library_container.edit())
        self.assertEqual(edit_modal.library_key, library_key)
        self.assertEqual(edit_modal.count, max_count)
        self.assertEqual(edit_modal.scored, scored)

    def test_no_library_shows_library_not_configured(self):
        """
        Scenario: Given I have a library, a course and library content xblock in a course
        When I go to studio unit page for library content block
        And I edit set library key to none
        Then I can see that library content block is misconfigured
        """
        expected_text = 'A library has not yet been selected.'
        expected_action = 'Select a Library'
        library_container = self._get_library_xblock_wrapper(self.unit_page.xblocks[0])

        # precondition check - the library block should be configured before we remove the library setting
        self.assertFalse(library_container.has_validation_not_configured_warning)

        edit_modal = StudioLibraryContentXBlockEditModal(library_container.edit())
        edit_modal.library_key = None
        library_container.save_settings()

        self.assertTrue(library_container.has_validation_not_configured_warning)
        self.assertIn(expected_text, library_container.validation_not_configured_warning_text)
        self.assertIn(expected_action, library_container.validation_not_configured_warning_text)

    def test_set_missing_library_shows_correct_label(self):
        """
        Scenario: Given I have a library, a course and library content xblock in a course
        When I go to studio unit page for library content block
        And I edit set library key to non-existent library
        Then I can see that library content block is misconfigured
        """
        nonexistent_lib_key = 'library-v1:111+111'
        expected_text = "Library is invalid, corrupt, or has been deleted."

        library_container = self._get_library_xblock_wrapper(self.unit_page.xblocks[0])

        # precondition check - assert library is configured before we remove it
        self.assertFalse(library_container.has_validation_error)

        edit_modal = StudioLibraryContentXBlockEditModal(library_container.edit())
        edit_modal.library_key = nonexistent_lib_key

        library_container.save_settings()

        self.assertTrue(library_container.has_validation_error)
        self.assertIn(expected_text, library_container.validation_error_text)

    def test_out_of_date_message(self):
        """
        Scenario: Given I have a library, a course and library content xblock in a course
        When I go to studio unit page for library content block
        Then I update the library being used
        Then I refresh the page
        Then I can see that library content block needs to be updated
        When I click on the update link
        Then I can see that the content no longer needs to be updated
        """
        expected_text = "This component is out of date. The library has new content."
        library_block = self._get_library_xblock_wrapper(self.unit_page.xblocks[0])

        self.assertFalse(library_block.has_validation_warning)
        self.assertIn("3 matching components", library_block.author_content)

        self.library_fixture.create_xblock(self.library_fixture.library_location, XBlockFixtureDesc("html", "Html4"))

        self.unit_page.visit()  # Reload the page

        self.assertTrue(library_block.has_validation_warning)
        self.assertIn(expected_text, library_block.validation_warning_text)

        library_block.refresh_children()

        self.unit_page.wait_for_page()  # Wait for the page to reload
        library_block = self._get_library_xblock_wrapper(self.unit_page.xblocks[0])

        self.assertFalse(library_block.has_validation_message)
        self.assertIn("4 matching components", library_block.author_content)
