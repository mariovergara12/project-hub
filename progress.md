# Project progress — November 13, 2026

The backend supports sign-in, profile editing, and browsing projects.
The frontend still needs to be built.

## What is done

- Users can sign in through Supabase.
- Users can view and edit their own profile.
- Users can browse, search, and filter open projects.
- Users can open a project to see its owner, requirements, skills, and interests.
- Private projects are visible only to their owner or team members.
- The frontend can request data from the backend.

## Sample data

The Supabase development database contains:

- 10 demo accounts and profiles: 8 students and 2 faculty.
- 10 projects: 6 open and 4 in other stages.
- 12 skills and 7 interests linked to users and projects.

The data setup script can run again without creating duplicates or resetting
existing edits and passwords. Demo login details stay in a private local file
and will not be committed.

## What was tested

- All 119 automated tests passed.
- Code style checks passed.
- Real demo accounts could sign in and read project data.
- Private projects were hidden from unrelated users.
- The database matched the current backend structure.

## Review status

Backend changes go to `backend` first, then to `main` after checks pass.
The sample data is already in Supabase.
