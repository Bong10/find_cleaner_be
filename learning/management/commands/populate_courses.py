from django.core.management.base import BaseCommand
from django.utils.text import slugify
from learning.models import Course, Module, Lesson, Quiz, Question, Answer

class Command(BaseCommand):
    help = 'Populates the database with the Professional Cleaning Course content'

    def handle(self, *args, **kwargs):
        self.stdout.write('Deleting old course data...')
        # Optional: Clear existing data to avoid duplicates during development
        Course.objects.filter(title="Professional Cleaning Masterclass").delete()

        self.stdout.write('Creating course...')
        course = Course.objects.create(
            title="Professional Cleaning Masterclass",
            slug="professional-cleaning-masterclass",
            description="A complete guide to professional cleaning standards, techniques, chemicals, and customer service.",
            level="BEGINNER",
            is_published=True,
            required_clean_level=1
        )

        # ==========================================
        # MODULE 1: Basic Cleaning Techniques
        # ==========================================
        module_1 = Module.objects.create(
            course=course,
            title="Basic Cleaning Techniques",
            description="Teach cleaners the core skills needed for everyday residential and commercial cleaning.",
            order=1
        )

        lessons_m1 = [
            {
                "title": "Introduction to Basic Cleaning",
                "content": """Cleaning is more than wiping surfaces — it involves understanding hygiene standards, correct tools, and efficient methods. This module teaches the essentials every professional cleaner must master."""
            },
            {
                "title": "Essential Tools & Materials Checklist",
                "content": """**Tools:**
• Microfibre cloths (multi-colour for different areas)
• Mop & bucket
• Vacuum cleaner
• Broom & dustpan
• Scrub brush
• Squeegee (for glass)
• Gloves

**Cleaning products:**
• Multi-surface cleaner
• Bathroom disinfectant
• Glass cleaner
• Degreaser
• Floor cleaner suitable for wood/tile
• Dish soap
• Air freshener (optional)"""
            },
            {
                "title": "Colour-Coding System",
                "content": """**To avoid cross-contamination:**
• **Red cloth:** Toilets
• **Yellow cloth:** Bathrooms (sinks, showers)
• **Blue cloth:** General surfaces (tables, counters)
• **Green cloth:** Kitchens

This is industry standard and increases professionalism."""
            },
            {
                "title": "Basic Cleaning Techniques",
                "content": """**✔ Dusting**
• Start from top to bottom
• Use a dry microfibre cloth
• Clean surfaces, picture frames, shelves
• Move items slightly instead of cleaning around them

**✔ Wiping Surfaces**
• Spray cleaner on the cloth, not directly on the surface
• Wipe in an “S” motion for maximum coverage
• Use appropriate cloth colour

**✔ Sweeping & Mopping**
• Sweep floors first
• Use a clean mop head
• Mop in straight lines or figure-8 pattern
• Leave the floor to dry before walking on it

**✔ Vacuuming**
• Check filters and bag before use
• Vacuum edges first, then middle
• Use attachments for sofas, corners, skirting boards"""
            },
            {
                "title": "How to Clean Each Area",
                "content": """**Living Room & Bedroom**
• Dust all surfaces
• Vacuum or sweep floors
• Clean mirrors
• Arrange cushions and bedding
• Empty bins

**Kitchen**
• Wipe countertops
• Clean hob
• Wipe cupboard doors
• Clean sink
• Take out trash
• Mop kitchen floors

**Bathroom**
• Clean sink
• Scrub toilet (inside & outside)
• Clean shower/bath area
• Wipe mirrors
• Empty bins
• Mop floors"""
            },
            {
                "title": "Time-Saving Techniques",
                "content": """• Always work from top to bottom
• Work from left to right, never randomly
• Carry products & tools in a caddy
• Finish one room before moving to the next"""
            },
            {
                "title": "Common Mistakes to Avoid",
                "content": """• Using the same cloth in bathroom & kitchen
• Spraying products directly on electronics
• Using bleach on coloured surfaces
• Forgetting to clean door handles and light switches"""
            }
        ]

        for i, l_data in enumerate(lessons_m1, 1):
            Lesson.objects.create(
                module=module_1,
                title=l_data["title"],
                content=l_data["content"],
                order=i,
                content_type='TEXT'
            )

        # Quiz for Module 1
        quiz_lesson_m1 = Lesson.objects.create(
            module=module_1,
            title="Module 1 Quiz",
            content="Test your knowledge on basic cleaning techniques.",
            order=len(lessons_m1) + 1,
            content_type='QUIZ'
        )
        quiz_m1 = Quiz.objects.create(lesson=quiz_lesson_m1, passing_score=80)

        q1_m1 = Question.objects.create(quiz=quiz_m1, text="What colour cloth should be used in the kitchen?", order=1)
        Answer.objects.create(question=q1_m1, text="Green", is_correct=True)
        Answer.objects.create(question=q1_m1, text="Red", is_correct=False)
        Answer.objects.create(question=q1_m1, text="Blue", is_correct=False)

        q2_m1 = Question.objects.create(quiz=quiz_m1, text="Why do we clean from top to bottom?", order=2)
        Answer.objects.create(question=q2_m1, text="Because dust falls downwards", is_correct=True)
        Answer.objects.create(question=q2_m1, text="It is faster", is_correct=False)

        q3_m1 = Question.objects.create(quiz=quiz_m1, text="What should you do before vacuuming?", order=3)
        Answer.objects.create(question=q3_m1, text="Check filters and bag", is_correct=True)
        Answer.objects.create(question=q3_m1, text="Mop the floor", is_correct=False)

        q4_m1 = Question.objects.create(quiz=quiz_m1, text="Is it okay to use bathroom cloths in the kitchen?", order=4)
        Answer.objects.create(question=q4_m1, text="No, never", is_correct=True)
        Answer.objects.create(question=q4_m1, text="Yes, if washed", is_correct=False)

        q5_m1 = Question.objects.create(quiz=quiz_m1, text="Which tool is essential for a cleaning caddy?", order=5)
        Answer.objects.create(question=q5_m1, text="Microfibre cloths", is_correct=True)
        Answer.objects.create(question=q5_m1, text="Hammer", is_correct=False)


        # ==========================================
        # MODULE 2: Deep Cleaning Techniques
        # ==========================================
        module_2 = Module.objects.create(
            course=course,
            title="Deep Cleaning Techniques",
            description="Teach cleaners how to perform professional deep cleans for kitchens, bathrooms, bedrooms, and full properties.",
            order=2
        )

        lessons_m2 = [
            {
                "title": "What Is Deep Cleaning?",
                "content": """Deep cleaning means cleaning areas that are not covered in regular cleaning, such as:
• Behind and under appliances
• Inside ovens, fridges, and cupboards
• Limescale removal
• Detailed scrubbing
• High-touch points

Deep cleaning takes more time and requires stronger chemicals and detailed work."""
            },
            {
                "title": "Tools & Equipment Required",
                "content": """• Heavy-duty degreaser
• Descaler/limescale remover
• Oven cleaner
• Stainless-steel cleaner
• Detail brush / old toothbrush
• Scraper blade (for ovens & hobs only, carefully)
• Steam cleaner (optional but very professional)
• Microfibre cloths (colour-coded)
• Bucket, mop, sponge pads"""
            },
            {
                "title": "Deep Cleaning Step-by-Step (Kitchen)",
                "content": """**1. Countertops & Surfaces**
• Remove everything first
• Degrease
• Scrub corners & backsplash
• Wipe down with clean microfibre cloth

**2. Hob/Stove**
• Apply degreaser
• Let sit for 5–10 minutes
• Scrub
• Use scraper on burnt food (glass hobs only)
• Polish with a dry cloth

**3. Oven (Most Important for End-of-Tenancy)**
• Remove racks
• Apply oven cleaner inside
• Let sit 20–40 minutes depending on strength
• Scrub and wipe
• Clean racks separately in sink
• Wipe door glass last

**4. Fridge & Freezer**
• Switch off first
• Remove shelves & drawers
• Clean all parts with warm soapy water
• Wipe inside fridge
• Dry completely before turning back on

**5. Cupboards (Inside & Outside)**
• Empty everything
• Wipe inside
• Clean doors
• Dry with microfibre cloth

**6. Sink**
• Use descaler for limescale
• Scrub around taps
• Polish with stainless steel spray"""
            },
            {
                "title": "Deep Cleaning Step-by-Step (Bathroom)",
                "content": """**1. Shower & Bath**
• Spray limescale remover
• Leave for 5–10 minutes
• Scrub tiles, glass, and taps
• Rinse thoroughly

**2. Toilet**
• Apply toilet gel
• Scrub inside
• Clean outside: base, lid, behind the toilet
• Wipe handle (high-touch point)

**3. Sink & Countertop**
• Use bathroom cleaner
• Detail brush around taps
• Wipe all surfaces

**4. Tiles**
• Spray degreaser or bathroom cleaner
• Scrub grout lines
• Rinse and dry

**5. Mirrors & Glass**
• Use glass cleaner
• Wipe with dry microfibre cloth"""
            },
            {
                "title": "Deep Cleaning Living Areas & Bedrooms",
                "content": """**1. Dusting Everywhere**
• High areas (light fixtures, top of cupboards)
• Behind furniture
• Light switches & door handles

**2. Walls & Skirting**
• Wipe skirting boards
• Spot clean walls

**3. Furniture**
• Move furniture to vacuum underneath
• Dust behind TV
• Clean windowsills

**4. Mattress (Optional)**
• Vacuum mattress
• Spray antibacterial fabric spray"""
            },
            {
                "title": "Flooring – Deep Clean",
                "content": """**Tiles / Hard Floors**
• Sweep
• Mop using strong floor cleaner
• Scrub grout if necessary

**Carpets**
• Vacuum thoroughly
• Edge clean corners
• Carpet shampoo or steam extractor (if available)"""
            },
            {
                "title": "High-Touch Points Checklist",
                "content": """Clean these during every deep clean:
• Door handles
• Light switches
• Remote controls
• Appliance handles
• Drawer knobs
• Stair rails"""
            },
            {
                "title": "Safety & Chemical Handling",
                "content": """• Always wear gloves
• Never mix bleach with other chemicals
• Check labels
• Ensure ventilation
• Keep chemicals away from clients’ children or pets"""
            }
        ]

        for i, l_data in enumerate(lessons_m2, 1):
            Lesson.objects.create(
                module=module_2,
                title=l_data["title"],
                content=l_data["content"],
                order=i,
                content_type='TEXT'
            )

        # Quiz for Module 2
        quiz_lesson_m2 = Lesson.objects.create(
            module=module_2,
            title="Module 2 Quiz",
            content="Test your knowledge on deep cleaning techniques.",
            order=len(lessons_m2) + 1,
            content_type='QUIZ'
        )
        quiz_m2 = Quiz.objects.create(lesson=quiz_lesson_m2, passing_score=80)

        q1_m2 = Question.objects.create(quiz=quiz_m2, text="How long should oven cleaner sit before scrubbing?", order=1)
        Answer.objects.create(question=q1_m2, text="20–40 minutes", is_correct=True)
        Answer.objects.create(question=q1_m2, text="1 minute", is_correct=False)

        q2_m2 = Question.objects.create(quiz=quiz_m2, text="What chemical removes limescale?", order=2)
        Answer.objects.create(question=q2_m2, text="Descaler / Limescale remover", is_correct=True)
        Answer.objects.create(question=q2_m2, text="Bleach", is_correct=False)

        q3_m2 = Question.objects.create(quiz=quiz_m2, text="Should you clean cupboards inside during deep clean?", order=3)
        Answer.objects.create(question=q3_m2, text="Yes, empty and wipe inside", is_correct=True)
        Answer.objects.create(question=q3_m2, text="No, only outside", is_correct=False)

        q4_m2 = Question.objects.create(quiz=quiz_m2, text="Name one high-touch point.", order=4)
        Answer.objects.create(question=q4_m2, text="Door handles", is_correct=True)
        Answer.objects.create(question=q4_m2, text="Ceiling", is_correct=False)

        q5_m2 = Question.objects.create(quiz=quiz_m2, text="Why should you move furniture during deep cleaning?", order=5)
        Answer.objects.create(question=q5_m2, text="To vacuum underneath", is_correct=True)
        Answer.objects.create(question=q5_m2, text="To exercise", is_correct=False)


        # ==========================================
        # MODULE 4: Handling Cleaning Chemicals (COSHH Basics)
        # ==========================================
        module_4 = Module.objects.create(
            course=course,
            title="Handling Cleaning Chemicals (COSHH Basics)",
            description="Teach cleaners how to safely handle chemicals according to COSHH standards.",
            order=3
        )

        lessons_m4 = [
            {
                "title": "What Is COSHH?",
                "content": """COSHH = rules that protect people from harmful chemicals.

In cleaning, COSHH applies to:
• Bleach
• Descalers
• Oven cleaners
• Disinfectants
• Degreasers
• Limescale removers
• Any chemical with warning signs

Cleaners must use chemicals safely, avoid injuries, and protect clients’ homes."""
            },
            {
                "title": "Chemical Warning Symbols",
                "content": """**🔥 Flammable**
Keep away from heat.

**☠️ Toxic**
Avoid breathing or touching.

**⚠️ Irritant / Harmful**
Can irritate skin or eyes.

**🧴 Corrosive**
Can burn skin or damage surfaces.

**🌊 Environmental Hazard**
Do not pour large amounts down drains."""
            },
            {
                "title": "Golden Rules of Chemical Safety",
                "content": """**✔ 1. Never mix chemicals**
Most important rule.
⚠️ Never mix:
• Bleach + any other chemical
• Bleach + toilet cleaner
• Bleach + vinegar
• Bleach + descaler
These combinations create dangerous gases.

**✔ 2. Wear protective gloves**
Always. Not optional.

**✔ 3. Read the label**
Before using any product:
• Check instructions
• Check dilution ratio
• Check surfaces it can/can’t be used on

**✔ 4. Use correct dilution**
Many chemicals are concentrated. Using too much can damage surfaces or cause breathing problems.

**✔ 5. Ensure ventilation**
Open windows when using strong chemicals like oven cleaner or bleach.

**✔ 6. Never spray chemicals near children or pets**

**✔ 7. Store chemicals safely**
Keep upright, in a caddy, away from food/clothes/children."""
            },
            {
                "title": "Chemical Categories",
                "content": """**A. General Cleaners**
Use for surfaces, tables, cupboards.

**B. Disinfectants**
Use in bathrooms, toilets, and high-touch areas.

**C. Degreasers**
Use in kitchens, ovens, extractor fans, and stoves.

**D. Descalers / Limescale Removers**
Use in showers, taps, sinks, kettles.

**E. Glass Cleaners**
Use on mirrors, windows, shower screens."""
            },
            {
                "title": "Where NOT to Use Certain Chemicals",
                "content": """**❌ Bleach**
• Not on coloured surfaces
• Not on metal taps
• Not on wooden floors
• Not near fabrics

**❌ Descaler**
• Not on marble
• Not on natural stone
• Not on aluminium

**❌ Oven Cleaner**
• Not on painted surfaces
• Avoid contact with skin"""
            },
            {
                "title": "Safe Sequence of Using Chemicals",
                "content": """To avoid accidents:
1. Put on gloves
2. Read the label
3. Test on a small area
4. Apply chemical
5. Let it sit if needed
6. Scrub
7. Rinse thoroughly
8. Wipe dry"""
            },
            {
                "title": "What to Do in Case of an Accident",
                "content": """**Chemical on skin:**
Rinse with water for 10 minutes.

**Chemical in eyes:**
Use eyewash or water for 10–15 minutes. Seek medical attention.

**Chemical spills:**
Wipe immediately with plenty of water."""
            }
        ]

        for i, l_data in enumerate(lessons_m4, 1):
            Lesson.objects.create(
                module=module_4,
                title=l_data["title"],
                content=l_data["content"],
                order=i,
                content_type='TEXT'
            )

        # Quiz for Module 4
        quiz_lesson_m4 = Lesson.objects.create(
            module=module_4,
            title="Module 4 Quiz",
            content="Test your knowledge on COSHH and chemical safety.",
            order=len(lessons_m4) + 1,
            content_type='QUIZ'
        )
        quiz_m4 = Quiz.objects.create(lesson=quiz_lesson_m4, passing_score=80)

        q1_m4 = Question.objects.create(quiz=quiz_m4, text="What is COSHH?", order=1)
        Answer.objects.create(question=q1_m4, text="Control of Substances Hazardous to Health", is_correct=True)
        Answer.objects.create(question=q1_m4, text="Cleaning of Surfaces in Homes", is_correct=False)

        q2_m4 = Question.objects.create(quiz=quiz_m4, text="Should you mix bleach with toilet cleaner?", order=2)
        Answer.objects.create(question=q2_m4, text="No, never", is_correct=True)
        Answer.objects.create(question=q2_m4, text="Yes, for better cleaning", is_correct=False)

        q3_m4 = Question.objects.create(quiz=quiz_m4, text="What chemical removes limescale?", order=3)
        Answer.objects.create(question=q3_m4, text="Descaler", is_correct=True)
        Answer.objects.create(question=q3_m4, text="Degreaser", is_correct=False)

        q4_m4 = Question.objects.create(quiz=quiz_m4, text="Name one chemical that must NOT be used on marble.", order=4)
        Answer.objects.create(question=q4_m4, text="Descaler / Acidic cleaners", is_correct=True)
        Answer.objects.create(question=q4_m4, text="Water", is_correct=False)

        q5_m4 = Question.objects.create(quiz=quiz_m4, text="Why is ventilation important?", order=5)
        Answer.objects.create(question=q5_m4, text="To avoid breathing harmful fumes", is_correct=True)
        Answer.objects.create(question=q5_m4, text="To dry the floor faster", is_correct=False)


        # ==========================================
        # MODULE 5: Customer Service & Professional Behaviour
        # ==========================================
        module_5 = Module.objects.create(
            course=course,
            title="Customer Service & Professional Behaviour",
            description="Teach cleaners how to act professionally, communicate well, and deliver a positive customer experience.",
            order=4
        )

        lessons_m5 = [
            {
                "title": "First Impression Matters",
                "content": """Clients judge cleaners in the first 30 seconds. A cleaner must always:

**✔ Dress professionally**
• Clean clothes, closed shoes, no strong perfume, no messy hair.
• Wear gloves during work.

**✔ Arrive on time**
• 5 minutes early = perfect.
• Never arrive late without notice.

**✔ Be polite**
• Smile, greet politely.
• Example: “Hello, I’m [Name], your cleaner from Find Cleaner. I’m here for your appointment.”"""
            },
            {
                "title": "Entering the Client’s Home",
                "content": """**✔ Ask before moving items**
**✔ Never open drawers unless required**
**✔ Never touch personal items**
**✔ Keep noise low**
**✔ Don’t answer personal calls during cleaning**"""
            },
            {
                "title": "Communication Skills",
                "content": """**✔ Ask what the client wants**
“Do you have any specific areas you want me to focus on today?”

**✔ Confirm the time needed**
“This will take approximately 2 hours. Is that okay?”

**✔ Update the client if something takes longer**

**✔ Be honest about what can or cannot be cleaned**
Example: “This stain is very old. I will try my best but it may not come out completely.”"""
            },
            {
                "title": "Professional Behaviour",
                "content": """**❌ Never sit on the client’s furniture**
**❌ Never eat or drink client’s food**
**❌ Never bring children or friends**
**❌ Never ask the client for personal favours**
**❌ Never argue with the client**

Cleaners represent your brand, so behaviour must always be 100% professional."""
            },
            {
                "title": "Protect Client’s Privacy",
                "content": """**✔ Never take photos of client’s property (except before/after cleaning for evidence)**
**✔ Never share client information**
**✔ Never discuss client’s home with others**"""
            },
            {
                "title": "Handling Complaints Professionally",
                "content": """If a client complains:
1. Stay calm
2. Listen without interrupting
3. Apologize politely
4. Offer to fix the issue

Example: “I’m really sorry about that. I’ll fix it immediately.”
Never argue. Never raise your voice."""
            },
            {
                "title": "How to Ask for Reviews",
                "content": """Client reviews help your platform grow.

Cleaners can say:
“If you were happy with the service, I’d appreciate if you leave a review on Find Cleaner. It helps me get more work.”

Always ask politely."""
            },
            {
                "title": "End-of-Service Routine",
                "content": """At the end of every cleaning:
✔ Show the client what you cleaned
✔ Ask if they are satisfied
✔ Put back all items in their place
✔ Empty bins
✔ Switch off lights used
✔ Close windows
✔ Say thank you"""
            }
        ]

        for i, l_data in enumerate(lessons_m5, 1):
            Lesson.objects.create(
                module=module_5,
                title=l_data["title"],
                content=l_data["content"],
                order=i,
                content_type='TEXT'
            )

        # Quiz for Module 5
        quiz_lesson_m5 = Lesson.objects.create(
            module=module_5,
            title="Module 5 Quiz",
            content="Test your knowledge on customer service.",
            order=len(lessons_m5) + 1,
            content_type='QUIZ'
        )
        quiz_m5 = Quiz.objects.create(lesson=quiz_lesson_m5, passing_score=80)

        q1_m5 = Question.objects.create(quiz=quiz_m5, text="What should a cleaner say when they arrive?", order=1)
        Answer.objects.create(question=q1_m5, text="Greet politely and introduce themselves", is_correct=True)
        Answer.objects.create(question=q1_m5, text="Nothing, just start cleaning", is_correct=False)

        q2_m5 = Question.objects.create(quiz=quiz_m5, text="Should cleaners sit on the client’s sofa?", order=2)
        Answer.objects.create(question=q2_m5, text="No, never", is_correct=True)
        Answer.objects.create(question=q2_m5, text="Yes, if tired", is_correct=False)

        q3_m5 = Question.objects.create(quiz=quiz_m5, text="What should you do if the client complains?", order=3)
        Answer.objects.create(question=q3_m5, text="Apologize and offer to fix it", is_correct=True)
        Answer.objects.create(question=q3_m5, text="Argue with them", is_correct=False)

        q4_m5 = Question.objects.create(quiz=quiz_m5, text="Why is privacy important?", order=4)
        Answer.objects.create(question=q4_m5, text="To protect the client's confidentiality", is_correct=True)
        Answer.objects.create(question=q4_m5, text="It is not important", is_correct=False)

        q5_m5 = Question.objects.create(quiz=quiz_m5, text="How do you ask for a review politely?", order=5)
        Answer.objects.create(question=q5_m5, text="Ask if they were happy, then request a review", is_correct=True)
        Answer.objects.create(question=q5_m5, text="Demand a review before leaving", is_correct=False)


        # ==========================================
        # MODULE 6: Professional Cleaning Standards
        # ==========================================
        module_6 = Module.objects.create(
            course=course,
            title="Professional Cleaning Standards",
            description="Provide cleaners with exact instructions on how each room should look when completed.",
            order=5
        )

        lessons_m6 = [
            {
                "title": "General Rules for Every Room",
                "content": """**✔ Work top → bottom**
Start from ceilings/light fixtures → end with floors.

**✔ Work left → right**
Ensures every corner gets covered.

**✔ Use colour-coded cloths**
• Red → Toilet
• Yellow → Bathroom
• Blue → Living/bedrooms
• Green → Kitchen

**✔ High-touch points must be cleaned**
Door handles, switches, remotes, appliance handles, drawer knobs.

**✔ Check the room before leaving**
No dust, no streaks, no marks, no rubbish left."""
            },
            {
                "title": "Living Room Standards",
                "content": """**✔ Dust:** TV stands, shelves, photo frames, lamps, window sills.
**✔ Clean:** Coffee tables, side tables, mirrors, doors & handles.
**✔ Vacuum:** Carpet thoroughly, under sofas, edges & corners.
**✔ Arrange:** Fold blankets, arrange cushions neatly, organise magazines.

**Final look:** A fresh, organised living room with no dust or streaks."""
            },
            {
                "title": "Bedroom Standards",
                "content": """**✔ Make the bed properly:** Smooth duvet, arrange pillows, no wrinkles.
**✔ Dust:** Bedside tables, headboard, drawers, mirrors.
**✔ Clean:** Wardrobe doors, door handles, light switches.
**✔ Vacuum:** Under the bed, carpets, corners.

**Final look:** A clean, peaceful room with a perfectly made bed."""
            },
            {
                "title": "Kitchen Standards",
                "content": """**✔ Surfaces:** Wipe counters, clean backsplash, degrease stove, clean microwave.
**✔ Appliances:** Wipe fridge exterior, clean cupboard doors, polish stainless steel.
**✔ Sink:** Remove limescale, scrub drain, polish taps.
**✔ Floors:** Sweep, mop well, no sticky spots.

**Final look:** Fresh, grease-free kitchen with shiny surfaces."""
            },
            {
                "title": "Bathroom Standards",
                "content": """**✔ Shower & Bath:** Remove soap scum & limescale, clean tiles, scrub glass.
**✔ Toilet:** Scrub inside, clean seat/base/behind, disinfect handle.
**✔ Sink:** Descale, polish taps, clean underneath.
**✔ Mirrors:** Clean streak-free.
**✔ Floor:** Mop disinfect, ensure dry.

**Final look:** Sparkling bathroom with no water marks or limescale."""
            },
            {
                "title": "Hallways & Entrances",
                "content": """**✔ Dust:** Skirting boards, radiators, shelves.
**✔ Clean:** Entry doors inside, handles, mirrors.
**✔ Floors:** Sweep or vacuum, mop if needed.

**Final look:** A welcoming entrance with a clean scent."""
            },
            {
                "title": "Balconies / Outdoor Areas",
                "content": """✔ Sweep floor
✔ Remove cobwebs
✔ Wipe railings
✔ Clean light fixtures
✔ Remove rubbish"""
            },
            {
                "title": "Final Inspection Checklist",
                "content": """Before marking the job complete, check:
✔ No dust anywhere
✔ No fingerprints on surfaces
✔ No streaks on mirrors/windows
✔ No marks on floors
✔ No rubbish left
✔ Everything arranged neatly
✔ No chemical smell (ventilate)
✔ Lights off & doors closed"""
            }
        ]

        for i, l_data in enumerate(lessons_m6, 1):
            Lesson.objects.create(
                module=module_6,
                title=l_data["title"],
                content=l_data["content"],
                order=i,
                content_type='TEXT'
            )

        # Quiz for Module 6
        quiz_lesson_m6 = Lesson.objects.create(
            module=module_6,
            title="Module 6 Quiz",
            content="Test your knowledge on professional cleaning standards.",
            order=len(lessons_m6) + 1,
            content_type='QUIZ'
        )
        quiz_m6 = Quiz.objects.create(lesson=quiz_lesson_m6, passing_score=80)

        q1_m6 = Question.objects.create(quiz=quiz_m6, text="Why do we clean from top to bottom?", order=1)
        Answer.objects.create(question=q1_m6, text="Because dust falls downwards", is_correct=True)
        Answer.objects.create(question=q1_m6, text="It is easier", is_correct=False)

        q2_m6 = Question.objects.create(quiz=quiz_m6, text="What colour cloth is used in the kitchen?", order=2)
        Answer.objects.create(question=q2_m6, text="Green", is_correct=True)
        Answer.objects.create(question=q2_m6, text="Red", is_correct=False)

        q3_m6 = Question.objects.create(quiz=quiz_m6, text="What must be cleaned before leaving every room?", order=3)
        Answer.objects.create(question=q3_m6, text="High-touch points and check for rubbish", is_correct=True)
        Answer.objects.create(question=q3_m6, text="The windows only", is_correct=False)

        q4_m6 = Question.objects.create(quiz=quiz_m6, text="What should a bathroom mirror look like when finished?", order=4)
        Answer.objects.create(question=q4_m6, text="Streak-free", is_correct=True)
        Answer.objects.create(question=q4_m6, text="Cloudy", is_correct=False)

        q5_m6 = Question.objects.create(quiz=quiz_m6, text="Why is left-to-right cleaning important?", order=5)
        Answer.objects.create(question=q5_m6, text="Ensures every corner gets covered", is_correct=True)
        Answer.objects.create(question=q5_m6, text="It is a tradition", is_correct=False)

        self.stdout.write(self.style.SUCCESS('Successfully populated course content!'))
