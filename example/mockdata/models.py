"""
Real Django models backing the package's example/demo data.
"""

from django.db import models


class Organization(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.CharField(max_length=4, primary_key=True)
    name = models.CharField(max_length=255)
    plan = models.CharField(max_length=20, choices=Plan.choices)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.name} ({self.plan})"


class Employee(models.Model):
    class Department(models.TextChoices):
        PRODUCT_ENGINEERING = "product_engineering", "Product Engineering"
        TECHNICAL_SUPPORT = "technical_support", "Technical Support"
        CUSTOMER_SUCCESS = "customer_success", "Customer Success"

    id = models.CharField(max_length=4, primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    department = models.CharField(max_length=30, choices=Department.choices)
    manager = models.CharField(max_length=255, default="")

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        ON_HOLD = "on_hold", "On Hold"

    id = models.CharField(max_length=6, primary_key=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return self.name


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    id = models.CharField(max_length=6, primary_key=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tickets"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    priority = models.PositiveSmallIntegerField()
    assignee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, related_name="tickets"
    )
    created_at = models.DateTimeField()
    comments = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return self.title
