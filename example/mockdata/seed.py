"""
Populates the (in-memory) database with fake data, generated the same way
the original dataclass-based mock data was.
"""

import random

from django.utils import timezone
from faker import Faker

from .models import Employee, Organization, Project, Ticket

ANIMALS = (
    "Capybara",
    "Fox",
    "Bear",
    "Eagle",
    "Wolf",
    "Tiger",
    "Hawk",
    "Lion",
    "Shark",
    "Rabbit",
    "Panda",
    "Dragon",
)
COLORS = (
    "Red",
    "Blue",
    "Green",
    "Black",
    "White",
    "Silver",
    "Gold",
    "Crimson",
    "Indigo",
    "Purple",
    "Scarlet",
)


def unique_numeric_id_generator(length: int = 6):
    used = set()
    min_val = 10 ** (length - 1)
    max_val = (10**length) - 1

    def _next_id() -> str:
        while True:
            val = random.randint(min_val, max_val)
            if val not in used:
                used.add(val)
                return str(val)

    return _next_id


def populate_mock_data() -> None:
    """Idempotent: does nothing if data already exists (e.g. re-import
    under the dev server's autoreloader)."""
    if Organization.objects.exists():
        return

    fake = Faker("en_US")
    Faker.seed(42)
    random.seed(42)

    org_id_gen = unique_numeric_id_generator(4)
    project_id_gen = unique_numeric_id_generator(6)
    ticket_id_gen = unique_numeric_id_generator(6)
    employee_id_gen = unique_numeric_id_generator(4)

    employees: list[Employee] = []
    organizations: list[Organization] = []
    projects: list[Project] = []
    tickets: list[Ticket] = []

    # Employees
    for _ in range(8):
        employees.append(
            Employee(
                id=employee_id_gen(),
                name=fake.name(),
                email=fake.company_email(),
                department=random.choice(Employee.Department.values),
                manager=fake.name() if random.random() > 0.8 else None,
            )
        )
    Employee.objects.bulk_create(employees)

    # Organizations, Projects, and Tickets
    for _ in range(12):
        org_id = org_id_gen()
        org = Organization(
            id=org_id, name=fake.company(), plan=random.choice(Organization.Plan.values)
        )
        organizations.append(org)

        for _ in range(random.randint(2, 6)):
            project_id = project_id_gen()
            project_name = f"{random.choice(COLORS)} {random.choice(ANIMALS)}"

            project = Project(
                id=project_id,
                organization=org,
                name=project_name,
                status=random.choice(Project.Status.values),
            )
            projects.append(project)

            for _ in range(random.randint(2, 15)):
                assignee = random.choice(employees)

                tickets.append(
                    Ticket(
                        id=ticket_id_gen(),
                        project=project,
                        title=fake.catch_phrase(),
                        description=fake.paragraph(nb_sentences=3),
                        status=random.choice(Ticket.Status.values),
                        priority=random.randint(1, 5),
                        assignee=assignee,
                        created_at=timezone.make_aware(fake.date_time_this_year()),
                        comments=[fake.sentence() for _ in range(random.randint(1, 5))],
                    )
                )

    Organization.objects.bulk_create(organizations)
    Project.objects.bulk_create(projects)
    Ticket.objects.bulk_create(tickets)
