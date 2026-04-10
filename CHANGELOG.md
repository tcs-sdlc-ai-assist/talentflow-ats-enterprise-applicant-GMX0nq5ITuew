# Changelog

All notable changes to the TalentFlow ATS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-15

### Added

#### Authentication & Security
- User registration with email validation and secure password hashing
- JWT-based authentication with access token issuance and verification
- Login and logout functionality with session management
- Password hashing using bcrypt for secure credential storage

#### Role-Based Access Control (RBAC)
- Support for multiple user roles: Super Admin, Hiring Manager, Recruiter, Interviewer, Read-Only
- Role-based route protection and endpoint authorization
- Role-aware UI rendering with conditional navigation and action visibility
- Permission enforcement across all API endpoints

#### Job Management
- Full CRUD operations for job postings (create, read, update, delete)
- Job status lifecycle management: Draft, Open, Closed, On Hold
- Job listing with filtering by status, department, and location
- Detailed job view with associated candidates and application counts
- Department and location metadata for job categorization

#### Candidate Management
- Candidate profile creation and management with contact details
- Resume and document tracking per candidate
- Candidate search and filtering capabilities
- Candidate detail view with full application history
- Skills and experience tracking for candidate profiles

#### Application Pipeline with Kanban
- Visual Kanban board for tracking application stages
- Configurable pipeline stages: Applied, Screening, Interview, Offer, Hired, Rejected
- Drag-and-drop stage transitions for application status updates
- Application creation linking candidates to job postings
- Stage history tracking with timestamps for each transition
- Filtering applications by job, stage, and candidate

#### Interview Scheduling & Feedback
- Interview scheduling with date, time, and location details
- Interviewer assignment to scheduled interviews
- Structured interview feedback submission with ratings
- Interview status tracking: Scheduled, Completed, Cancelled
- Interview calendar view for interviewers and hiring managers
- Feedback review and aggregation per candidate application

#### Role-Based Dashboards
- Super Admin dashboard with system-wide metrics and user management
- Hiring Manager dashboard with job-specific pipeline overview
- Recruiter dashboard with candidate sourcing and application metrics
- Interviewer dashboard with upcoming interviews and pending feedback
- Key performance indicators displayed per role context
- Recent activity feeds tailored to user role

#### Audit Trail
- Comprehensive audit logging for all create, update, and delete operations
- Actor tracking with user identification for every logged action
- Timestamp recording for all audited events
- Resource type and resource ID tracking for full traceability
- Audit log viewing interface for administrators

#### Technical Foundation
- FastAPI backend with async request handling
- SQLAlchemy 2.0 async ORM with SQLite (aiosqlite) database
- Pydantic v2 schemas for request/response validation
- Jinja2 server-side rendered templates with Tailwind CSS styling
- Modular project structure with routers, services, models, and schemas
- CORS middleware configuration for cross-origin support
- Structured logging throughout the application
- Lifespan-based startup and shutdown event handling