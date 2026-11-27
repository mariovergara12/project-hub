// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ProjectRecommendations } from '../src/Recommendations';
import type { Project, RecommendedProjects } from '../src/types';

const mocks = vi.hoisted(() => ({ resource: vi.fn(), reload: vi.fn() }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
const project: Project = { id: 'project-a', title: 'Campus map', description: 'Build an accessible campus map', project_type: 'student_project', status: 'open', weekly_hours: 5, minimum_experience_years: 1, member_count: 1, max_members: 4, owner: { id: 'owner', display_name: 'Maya', role: 'student', faculty_verified: false }, skills: [], interests: [], created_at: '', updated_at: '' };
const data: RecommendedProjects = { items: [{ project, score: 75, reasons: ['Shared skills: react', 'Shared interests: accessibility'], cautions: ['Time: needs 5 hrs/week; you listed 3'] }], missing_fields: [] };
function show() { return render(<MemoryRouter><ProjectRecommendations /></MemoryRouter>); }
beforeEach(() => { vi.resetAllMocks(); mocks.resource.mockReturnValue({ data, loading: false, reload: mocks.reload }); });
afterEach(cleanup);
it('shows the score, actual match reasons, project link, and requirements to check', async () => {
    show();
    expect(mocks.resource).toHaveBeenCalledWith('/projects/recommended');
    expect(screen.getByLabelText('75 match points out of 100')).toBeTruthy();
    expect(screen.getByRole('list', { name: 'Why Campus map matches' }).textContent).toContain('Shared skills: react');
    expect(screen.getByRole('link', { name: /View project/ }).getAttribute('href')).toBe('/projects/project-a');
    await userEvent.setup().click(screen.getByText('1 requirement to check'));
    expect(screen.getByText('Time: needs 5 hrs/week; you listed 3').closest('details')?.open).toBe(true);
});
it('shows only three suggestions until the user expands the list', async () => {
    const items = Array.from({ length: 5 }, (_, index) => ({ ...data.items[0], project: { ...project, id: `p-${index}`, title: `Project ${index}` } }));
    mocks.resource.mockReturnValue({ data: { ...data, items }, loading: false });
    show(); const user = userEvent.setup();
    expect(screen.getAllByRole('link', { name: /View project/ })).toHaveLength(3);
    await user.click(screen.getByRole('button', { name: 'Show all 5 matches' }));
    expect(screen.getAllByRole('link', { name: /View project/ })).toHaveLength(5);
    expect(screen.getByRole('button', { name: 'Show fewer matches' }).getAttribute('aria-expanded')).toBe('true');
    await user.click(screen.getByRole('button', { name: 'Show fewer matches' }));
    expect(screen.getAllByRole('link', { name: /View project/ })).toHaveLength(3);
});
it('asks for profile details when no matching signals have been saved', () => {
    mocks.resource.mockReturnValue({ data: { items: [], missing_fields: ['skills', 'interests', 'availability_hours', 'experience_years'] }, loading: false }); show();
    expect(screen.getByRole('heading', { name: 'Make your first matches' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Set up your profile' }).getAttribute('href')).toBe('/profile');
    expect(screen.queryByText('No matches right now')).toBeNull();
    expect(screen.queryByRole('link', { name: /View project/ })).toBeNull();
});
it('shows useful matches even when part of the profile is missing', () => {
    mocks.resource.mockReturnValue({ data: { ...data, missing_fields: ['availability_hours'] }, loading: false }); show();
    expect(screen.getByText(/For better matches, add weekly availability/)).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Campus map' })).toBeTruthy();
});
it('has a clear empty state when there are no positive eligible matches', () => {
    mocks.resource.mockReturnValue({ data: { items: [], missing_fields: [] }, loading: false }); show();
    expect(screen.getByRole('heading', { name: 'No matches right now' })).toBeTruthy();
    expect(screen.queryByText('Make your first matches')).toBeNull();
});
it('offers retry and browsing instead of showing a broken recommendation list', async () => {
    mocks.resource.mockReturnValue({ error: new Error('Unavailable'), loading: false, reload: mocks.reload }); show();
    expect(screen.getByRole('alert').textContent).toContain('browse all projects below');
    expect(screen.queryByText('Campus map')).toBeNull();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry recommendations' }));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('provides a manual refresh for current project availability', async () => {
    show();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh recommendations' }));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('shows loading without old cards or actionable refresh controls', () => {
    mocks.resource.mockReturnValue({ loading: true }); show();
    expect(screen.getByRole('status').textContent).toContain('Finding projects');
    expect((screen.getByRole('button', { name: 'Refresh recommendations' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByRole('heading', { name: 'Campus map' })).toBeNull();
});
it('explains how scores are calculated without requiring an external AI service', async () => {
    show(); await userEvent.setup().click(screen.getByText('How matching works'));
    const explanation = screen.getByText(/Shared skills contribute up to 50 points/);
    expect(explanation.closest('details')?.open).toBe(true);
    expect(explanation.textContent).toContain('Missing details earn no points');
    expect(within(screen.getByRole('region', { name: 'Recommended for you' })).getByRole('link', { name: 'Update profile' })).toBeTruthy();
});
