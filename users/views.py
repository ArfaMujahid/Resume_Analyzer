from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomUserCreationForm, UserProfileForm, UserSettingsForm
from .models import User, UserProfile

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_talent:
            return reverse_lazy('talent:dashboard')
        elif user.is_recruiter:
            return reverse_lazy('recruiter:dashboard')
        elif user.is_admin_user:
            return reverse_lazy('admin:index')
        return reverse_lazy('core:home')

class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Create user profile
        UserProfile.objects.create(user=self.object)
        messages.success(self.request, 'Account created successfully! Please log in.')
        return response

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        return context

class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

class SettingsView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserSettingsForm
    template_name = 'users/settings.html'
    success_url = reverse_lazy('users:settings')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Settings updated successfully!')
        return super().form_valid(form)
