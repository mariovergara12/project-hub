// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { MyTeams } from '../src/MyTeams';
import type { Project } from '../src/types';
const mocks = vi.hoisted(() => ({ resource: vi.fn(), reload: vi.fn() }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
const project: Project = { id: 'team-a', title: 'Campus team', description: 'Work together', status: 'in_progress', project_type: 'student_project', owner: { id: 'owner', display_name: 'Maya', role: 'student', faculty_verified: false }, member_count: 2, max_members: 4, weekly_hours: 5, minimum_experience_years: null, skills: [], interests: [], created_at: '', updated_at: '' };
const page = { items: [{ project, joined_at: null, is_owner: false }], next_cursor: 'next' };
function show(path = '/my-teams') { return render(<MemoryRouter initialEntries={[path]}><MyTeams /></MemoryRouter>); }
beforeEach(() => { vi.resetAllMocks(); mocks.resource.mockReturnValue({ data: page, loading: false, reload: mocks.reload }); });
afterEach(cleanup);
it('links current membership to the roster and distinguishes owners', () => {
    show(); expect(screen.getByText('Team member')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'View team' }).getAttribute('href')).toBe('/projects/team-a/team');
    expect(screen.getByText('2 / 4 members')).toBeTruthy();
});
it('preserves the status filter on pagination and resets the cursor when changing filters', async () => {
    show('/my-teams?status=in_progress'); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    expect(mocks.resource).toHaveBeenLastCalledWith('/me/teams?limit=12&status=in_progress&cursor=next');
    await user.selectOptions(screen.getByLabelText('Project status'), 'archived');
    expect(mocks.resource).toHaveBeenLastCalledWith('/me/teams?limit=12&status=archived');
});
it('offers discovery for an empty membership list and keeps history separate', () => {
    mocks.resource.mockReturnValue({ data: { items: [], next_cursor: null }, loading: false }); show();
    expect(screen.getByRole('heading', { name: 'Find your next team' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'View application history' }).getAttribute('href')).toBe('/my-applications');
});
it('does not show stale membership cards after a failure and offers a retry', async () => {
    mocks.resource.mockReturnValue({ error: new Error('Offline'), loading: false, reload: mocks.reload }); show();
    expect(screen.queryByText('Campus team')).toBeNull();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry teams' }));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
