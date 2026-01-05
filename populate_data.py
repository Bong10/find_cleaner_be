import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tidy_linker.settings')
django.setup()

from learning.models import Course, Instructor, CourseLearningOutcome

def populate():
    print("Populating data...")

    # 1. Create Instructor (Find Cleaner)
    instructor, created = Instructor.objects.get_or_create(
        name="Find Cleaner",
        defaults={
            "title": "Professional Cleaning Platform",
            "bio": "The official training certification from Find Cleaner. We set the industry standards for professional cleaning services, connecting thousands of qualified cleaners with employers every day.",
            "rating": 4.9,
            "students_count": 1250,
            "courses_count": 5
        }
    )
    if created:
        print(f"Created Instructor: {instructor.name}")
    else:
        print(f"Found Instructor: {instructor.name}")

    # 2. Create Course
    course_data = {
        "title": "Professional Cleaning Masterclass",
        "slug": "professional-cleaning-masterclass",
        "description": "Become a certified professional cleaner with our comprehensive masterclass. Learn industry-standard techniques, safety protocols, and how to manage your cleaning business effectively. This course covers everything from basic dusting to advanced chemical handling.",
        "level": "BEGINNER",
        "is_published": True,
        "price": 0.00,
        "original_price": 0.00,
        "duration_display": "Self-paced",
        "instructor": instructor,
        "articles_count": 5,
        "downloadable_resources_count": 12,
        "has_certificate": True,
        "access_devices": ["Mobile", "Desktop", "Tablet", "TV"],
        "required_clean_level": 0
    }

    course, created = Course.objects.update_or_create(
        slug="professional-cleaning-masterclass",
        defaults=course_data
    )
    
    if created:
        print(f"Created Course: {course.title}")
    else:
        print(f"Updated Course: {course.title}")

    # 3. Create Learning Outcomes
    outcomes = [
        "Master professional cleaning techniques for residential and commercial spaces",
        "Understand safety protocols, chemical handling, and PPE usage",
        "Efficiently manage time, resources, and client expectations",
        "Get certified and boost your career opportunities on Find Cleaner"
    ]

    # Clear existing outcomes to avoid duplicates if running multiple times
    CourseLearningOutcome.objects.filter(course=course).delete()

    for i, text in enumerate(outcomes):
        CourseLearningOutcome.objects.create(
            course=course,
            text=text,
            order=i
        )
    print(f"Added {len(outcomes)} learning outcomes.")

    print("Data population complete.")

if __name__ == '__main__':
    populate()
