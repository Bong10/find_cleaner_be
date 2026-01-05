from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Instructor(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='instructors/', null=True, blank=True)
    title = models.CharField(max_length=100)
    bio = models.TextField()
    rating = models.FloatField(default=5.0)
    students_count = models.IntegerField(default=0)
    courses_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Course(models.Model):
    LEVEL_CHOICES = (
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', null=True, blank=True, default='courses/thumbnails/cleaning_course.jpg')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='BEGINNER')
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Pricing & Marketing
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    original_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    duration_display = models.CharField(max_length=50, help_text="e.g. '12h 30m'", blank=True)
    
    # Instructor
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')

    # Features
    articles_count = models.IntegerField(default=0)
    downloadable_resources_count = models.IntegerField(default=0)
    has_certificate = models.BooleanField(default=True)
    access_devices = models.JSONField(default=list, help_text="List of devices e.g. ['Mobile', 'TV']")
    
    # Optional: Link to a specific cleaner level requirement or reward
    required_clean_level = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('VIDEO', 'Video'),
        ('TEXT', 'Text'),
        ('QUIZ', 'Quiz'),
    )

    module = models.ForeignKey(Module, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES, default='TEXT')
    content = models.TextField(help_text="Text content or Video URL")
    video_file = models.FileField(upload_to='courses/videos/', null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz')
    passing_score = models.IntegerField(default=70, validators=[MinValueValidator(0), MaxValueValidator(100)])

    def __str__(self):
        return f"Quiz for {self.lesson.title}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='enrollments', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='enrollments', on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

class LessonProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, related_name='lesson_progress', on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('enrollment', 'lesson')

class CourseLearningOutcome(models.Model):
    course = models.ForeignKey(Course, related_name='learning_outcomes', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_code = models.CharField(max_length=50, unique=True)
    file = models.FileField(upload_to='certificates/', null=True, blank=True)

    def __str__(self):
        return f"Certificate for {self.enrollment}"
