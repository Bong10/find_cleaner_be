from rest_framework import serializers
from .models import Course, Module, Lesson, Quiz, Question, Answer, Enrollment, LessonProgress, Instructor, CourseLearningOutcome

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text', 'is_correct']

class PublicAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    answers = PublicAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'answers']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'passing_score', 'questions']

class LessonSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    quiz = QuizSerializer(read_only=True)

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'content_type', 'content', 'video_file', 'duration_minutes', 'order', 'is_completed', 'quiz']

    def get_is_completed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return LessonProgress.objects.filter(enrollment__user=user, lesson=obj).exists()
        return False

class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'lessons']

class InstructorSerializer(serializers.ModelSerializer):
    students = serializers.IntegerField(source='students_count')

    class Meta:
        model = Instructor
        fields = ['name', 'image', 'title', 'bio', 'rating', 'students', 'courses_count']

class CourseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'thumbnail', 'level', 'description', 'required_clean_level']

class CourseDetailSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    # New fields
    originalPrice = serializers.DecimalField(source='original_price', max_digits=6, decimal_places=2)
    discount_percentage = serializers.SerializerMethodField()
    duration = serializers.CharField(source='duration_display')
    learning_outcomes = serializers.SlugRelatedField(many=True, read_only=True, slug_field='text')
    instructor_details = InstructorSerializer(source='instructor', read_only=True)
    features = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'price', 'originalPrice', 'discount_percentage', 'duration', 
                  'learning_outcomes', 'instructor_details', 'features',
                  'description', 'thumbnail', 'level', 'modules', 'is_enrolled', 'progress']

    def get_discount_percentage(self, obj):
        if obj.original_price and obj.original_price > 0:
            return int(((obj.original_price - obj.price) / obj.original_price) * 100)
        return 0

    def get_features(self, obj):
        return {
            "articles": obj.articles_count,
            "resources": obj.downloadable_resources_count,
            "certificate": obj.has_certificate,
            "access_devices": obj.access_devices
        }

    def get_is_enrolled(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False

    def get_progress(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=user, course=obj).first()
            if enrollment:
                return enrollment.progress_percent
        return 0

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'enrolled_at', 'progress_percent', 'is_completed', 'completed_at']
