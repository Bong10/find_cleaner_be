from django.test import TestCase
from users.models import User, Role,Cleaner,Employer
from django.contrib.auth import get_user_model
from job.models import Job,JobApplication,Service,JobBooking
class UserModelTestCase(TestCase):

    def setUp(self):
        # Créer un rôle
        self.role = Role.objects.create(name='Admin')
        self.service=Service.objects.create(name="service")
        # Créer un utilisateur
        self.user = User.objects.create_user(
            email="user@example.com",
            phone_number="+237678901234",
            name="John Doe",
            address="123 Street",
            gender="Male",
            role=self.role,
            password="password123"
        )

        self.cleaner=Cleaner.objects.create(
            user=self.user,
            portfolio="my portfolio",
            years_of_experience =4,
            dbs_check=True,
            insurance_details="sdkslks"

        )
        self.employer=Employer.objects.create(
            user=self.user,
            business_name="daki",
            location="ccc"
        )


        self.myfirst_job=Job.objects.create(
           employer=self.employer,
           location="ccc",
           status="p",
           special_requirements="nothing",
           time="10:20",
           date="2024-12-12",
           service=self.service
        )
        self.mysecond_job=Job.objects.create(
           employer=self.employer,
           location="dakar",
           status="p",
           special_requirements="nothing",
           time="11:20",
           date="2024-12-29",
           service=self.service
        )

    def test_user_creation(self):
        # Vérifier que l'utilisateur a bien été créé
        user = User.objects.get(email="user@example.com")
        self.assertEqual(user.name, "John Doe")
        self.assertEqual(user.phone_number, "+237678901234")
        self.assertEqual(user.address, "123 Street")
        self.assertEqual(user.gender, "Male")
        self.assertEqual(user.role.name, "Admin")
        self.assertTrue(user.check_password("password123"))

    def test_user_str_method(self):
        # Tester la méthode __str__ de l'utilisateur
        self.assertEqual(str(self.user), "user@example.com")

    def test_user_is_active_default(self):
        # Vérifier que l'utilisateur n'est pas actif par défaut
        self.assertFalse(self.user.is_active)
    
    def test_emplolyer_creation(self):
        user = User.objects.get(email="user@example.com")

    def test_apply_for_job_success(self):
        """
        Test successful job application
        """
        # Tenter de postuler pour un job
        result = JobApplication.applyForJob(
            job_id=self.myfirst_job.pk, 
            cleaner_id=self.cleaner.pk
        )

        # Vérifier que la candidature a été créée
        self.assertTrue(result)
        
        # Vérifier que l'application existe
        application = JobApplication.objects.get(
            job_id=self.myfirst_job.pk, 
            cleaner_id=self.cleaner.pk
        )
        
        # Vérifications supplémentaires
        self.assertEqual(application.status, "p")
        self.assertIsNotNone(application.date_applied)

    def test_duplicate_job_application(self):
        """
        Test prevention of duplicate job applications
        """
        # Première candidature
        first_result = JobApplication.applyForJob(
            job_id=self.myfirst_job.pk, 
            cleaner_id=self.cleaner.pk
        )
        self.assertTrue(first_result)

        # Deuxième candidature pour le même job
        second_result = JobApplication.applyForJob(
            job_id=self.myfirst_job.pk, 
            cleaner_id=self.cleaner.pk
        )
        self.assertFalse(second_result)

        # Vérifier qu'il n'y a qu'une seule candidature
        applications = JobApplication.objects.filter(
            job_id=self.myfirst_job, 
            cleaner_id=self.cleaner
        )
        self.assertEqual(len(applications), 1)

