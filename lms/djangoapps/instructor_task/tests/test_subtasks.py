"""
Unit tests for instructor_task subtasks.
"""
from uuid import uuid4

from mock import Mock, patch

from student.models import CourseEnrollment

from instructor_task.subtasks import queue_subtasks_for_query, _get_number_of_subtasks
from bulk_email.tasks import _get_chunks_from_queryset
from instructor_task.tests.factories import InstructorTaskFactory
from instructor_task.tests.test_base import InstructorTaskCourseTestCase


class TestSubtasks(InstructorTaskCourseTestCase):
    """Tests for subtasks."""

    def setUp(self):
        super(TestSubtasks, self).setUp()
        self.initialize_course()

    def _enroll_students_in_course(self, course_id, num_students):
        """Create and enroll some students in the course."""

        for _ in range(num_students):
            random_id = uuid4().hex[:8]
            self.create_student(username='student{0}'.format(random_id))

    def _queue_subtasks(self, create_subtask_fcn, items_per_query, items_per_task, initial_count, extra_count):
        """Queue subtasks while enrolling more students into course in the middle of the process."""

        task_id = str(uuid4())
        instructor_task = InstructorTaskFactory.create(
            course_id=self.course.id,
            task_id=task_id,
            task_key='dummy_task_key',
            task_type='bulk_course_email',
        )

        self._enroll_students_in_course(self.course.id, initial_count)
        task_queryset = CourseEnrollment.objects.filter(course_id=self.course.id)
        total_num_items = task_queryset.count()
        total_num_subtasks = _get_number_of_subtasks(total_num_items, items_per_query, items_per_task)

        task_queryset_generator = _get_chunks_from_queryset(
            task_queryset, items_per_query, 'pk', ['pk']
        )

        def initialize_subtask_info(*args):  # pylint: disable=unused-argument
            """Instead of initializing subtask info enroll some more students into course."""
            self._enroll_students_in_course(self.course.id, extra_count)
            return {}

        with patch('instructor_task.subtasks.initialize_subtask_info') as mock_initialize_subtask_info:
            mock_initialize_subtask_info.side_effect = initialize_subtask_info
            queue_subtasks_for_query(
                entry=instructor_task,
                action_name='action_name',
                create_subtask_fcn=create_subtask_fcn,
                recipient_qsets_generator=task_queryset_generator,
                total_num_items=total_num_items,
                total_num_subtasks=total_num_subtasks,
                item_fields=None,
                items_per_task=items_per_task,
            )

    def _test_queue_subtasks_for_query1(self):
        """
        Test queue_subtasks_for_query() if in last query the subtasks
        only need to accommodate < items_per_tasks items.
        """

        mock_create_subtask_fcn = Mock()
        self._queue_subtasks(mock_create_subtask_fcn, 6, 3, 8, 1)

        # Check number of items for each subtask
        mock_create_subtask_fcn_args = mock_create_subtask_fcn.call_args_list
        self.assertEqual(len(mock_create_subtask_fcn_args[0][0][0]), 3)
        self.assertEqual(len(mock_create_subtask_fcn_args[1][0][0]), 3)
        self.assertEqual(len(mock_create_subtask_fcn_args[2][0][0]), 3)

    def _test_queue_subtasks_for_query2(self):
        """
        Test queue_subtasks_for_query() if in last query the subtasks
        need to accommodate > items_per_task items.
        """

        mock_create_subtask_fcn = Mock()
        self._queue_subtasks(mock_create_subtask_fcn, 6, 3, 8, 3)

        # Check number of items for each subtask
        mock_create_subtask_fcn_args = mock_create_subtask_fcn.call_args_list
        self.assertEqual(len(mock_create_subtask_fcn_args[0][0][0]), 3)
        self.assertEqual(len(mock_create_subtask_fcn_args[1][0][0]), 3)
        self.assertEqual(len(mock_create_subtask_fcn_args[2][0][0]), 5)

    def test_queue_subtasks_for_query3(self):
        """
        Test queue_subtasks_for_query() if in last query the number of items
        available > items_per_query.
        """

        mock_create_subtask_fcn = Mock()

        self._queue_subtasks(mock_create_subtask_fcn, 6, 3, 11, 3)

        # Check number of items for each subtask
        mock_create_subtask_fcn_args = mock_create_subtask_fcn.call_args_list
        self.assertEqual(len(mock_create_subtask_fcn_args[0][0][0]), 3)
        self.assertEqual(len(mock_create_subtask_fcn_args[1][0][0]), 3)
        self.assertEqual(len(mock_create_subtask_fcn_args[2][0][0]), 4)
        self.assertEqual(len(mock_create_subtask_fcn_args[3][0][0]), 4)
