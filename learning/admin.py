from django.contrib import admin
from .models import Course, Module, Lesson, Quiz, Question, Answer, Enrollment, Certificate

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1

class ModuleInline(admin.StackedInline):
    model = Module
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'is_published', 'created_at')
    list_filter = ('level', 'is_published')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    inlines = [LessonInline]

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'progress_percent', 'is_completed', 'enrolled_at')
    list_filter = ('is_completed', 'course')

admin.site.register(Lesson)
admin.site.register(Quiz)
admin.site.register(Certificate)
