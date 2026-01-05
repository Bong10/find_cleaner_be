from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Course, Enrollment, Lesson, LessonProgress
from .serializers import CourseListSerializer, CourseDetailSerializer, EnrollmentSerializer, LessonSerializer

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.filter(is_published=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseListSerializer

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, slug=None):
        course = self.get_object()
        user = request.user
        
        if Enrollment.objects.filter(user=user, course=course).exists():
            return Response({"detail": "Already enrolled"}, status=status.HTTP_400_BAD_REQUEST)
            
        enrollment = Enrollment.objects.create(user=user, course=course)
        serializer = EnrollmentSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def submit_quiz(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get('lesson_id')
        answers = request.data.get('answers')  # Expecting {question_id: answer_id}
        
        if not lesson_id or not answers:
            return Response({"detail": "Lesson ID and answers required"}, status=status.HTTP_400_BAD_REQUEST)
            
        lesson = get_object_or_404(Lesson, id=lesson_id, module__course=enrollment.course)
        
        if not hasattr(lesson, 'quiz'):
            return Response({"detail": "This lesson does not have a quiz"}, status=status.HTTP_400_BAD_REQUEST)
            
        quiz = lesson.quiz
        total_questions = quiz.questions.count()
        correct_answers = 0
        
        for question in quiz.questions.all():
            submitted_answer_id = answers.get(str(question.id))
            if submitted_answer_id:
                # Check if the submitted answer is correct
                is_correct = question.answers.filter(id=submitted_answer_id, is_correct=True).exists()
                if is_correct:
                    correct_answers += 1
        
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        passed = score >= quiz.passing_score
        
        if passed:
            # Mark lesson as complete
            LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
            
            # Update course progress
            total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
            completed_lessons = LessonProgress.objects.filter(enrollment=enrollment).count()
            
            if total_lessons > 0:
                enrollment.progress_percent = (completed_lessons / total_lessons) * 100
                if enrollment.progress_percent == 100:
                    enrollment.is_completed = True
                    enrollment.completed_at = timezone.now()
                enrollment.save()
        
        return Response({
            "passed": passed,
            "score": score,
            "passing_score": quiz.passing_score,
            "progress": enrollment.progress_percent
        })

    @action(detail=True, methods=['post'])
    def complete_lesson(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get('lesson_id')
        
        if not lesson_id:
            return Response({"detail": "Lesson ID required"}, status=status.HTTP_400_BAD_REQUEST)
            
        lesson = get_object_or_404(Lesson, id=lesson_id, module__course=enrollment.course)
        
        # Record progress
        LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        
        # Update progress percentage
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        completed_lessons = LessonProgress.objects.filter(enrollment=enrollment).count()
        
        if total_lessons > 0:
            enrollment.progress_percent = (completed_lessons / total_lessons) * 100
            if enrollment.progress_percent == 100:
                enrollment.is_completed = True
                enrollment.completed_at = timezone.now()
                # Here you could trigger certificate generation
            enrollment.save()
            
        return Response({
            "status": "Lesson completed",
            "progress": enrollment.progress_percent,
            "is_completed": enrollment.is_completed
        })
