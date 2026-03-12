from django.db import models
import json

# Candidate Model for Portal
class Candidate(models.Model):
    PROFICIENCY_CHOICES = [
        ('Entry', 'Entry'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Expert', 'Expert'),
    ]
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('Internal', 'Internal'),
        ('External', 'External'),
    ]
    
    candidate_name = models.CharField(max_length=255)
    skills = models.CharField(max_length=255, blank=True)
    current_role = models.CharField(max_length=255)
    proficiency_level = models.CharField(max_length=50, choices=PROFICIENCY_CHOICES, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    employment_type = models.CharField(max_length=50, choices=EMPLOYMENT_TYPE_CHOICES, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    skill_vectors = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['candidate_name']
        verbose_name_plural = "Candidates"
        unique_together = ['candidate_name', 'email']
    
    def get_skill_vectors(self):
        """Return skill_vectors as list, handling None case"""
        if self.skill_vectors is None:
            return []
        if isinstance(self.skill_vectors, str):
            try:
                return json.loads(self.skill_vectors)
            except:
                return []
        return self.skill_vectors if isinstance(self.skill_vectors, list) else []
    
    def __str__(self):
        return f"{self.candidate_name} - {self.current_role}"
