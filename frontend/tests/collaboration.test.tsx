// @vitest-environment jsdom
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MyApplications, ProjectApplicants, ProjectParticipation, ProjectTeam } from '../src/Collaboration';
import { ApiError } from '../src/lib/api-client';
import type { ApplicationRecord, Me, Project, Team } from '../src/types';

const mocks = vi.hoisted(() => ({ resource: vi.fn(), post: vi.fn(), patch: vi.fn(), remove: vi.fn(), reload: vi.fn() }));
vi.mock('../src/api', () => ({ api: { post: mocks.post, patch: mocks.patch, delete: mocks.remove } }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource, refreshResources: vi.fn() }));
vi.mock('../src/AccountAccess', () => ({ AccountAccess: () => null }));
const owner: Project['owner'] = { id: 'owner', display_name: 'Maya', role: 'student', faculty_verified: false };
const applicant: Project['owner'] = { ...owner, id: 'applicant', display_name: 'Noah' };
const me: Me = { id: 'applicant', role: 'student', faculty_verified_at: null, profile: null, skills: [], interests: [] };
const project: Project = { id: 'project-a', owner, title: 'Campus library', description: 'Build together',
    status: 'open', project_type: 'student_project', member_count: 1, max_members: 2,
    weekly_hours: null, minimum_experience_years: null, skills: [], interests: [], created_at: '', updated_at: '' };
const summary = { id: project.id, title: project.title, status: project.status, owner_id: owner.id };
const application: ApplicationRecord = { id: 'app-a', applicant, project: summary, status: 'pending', message: 'I can help', created_at: '', updated_at: '' };
const team: Team = { project: summary, max_members: 2, member_count: 2, next_cursor: null,
    items: [{ user: owner, joined_at: '', is_owner: true }, { user: applicant, joined_at: '', is_owner: false }] };
function data(value: unknown) { return { data: value, loading: false, reload: mocks.reload }; }
function setup({ current, role = me, roster = team, status = 'open' }: {
    current?: ApplicationRecord; role?: Me; roster?: Team; status?: Project['status'];
} = {}) {
    mocks.resource.mockImplementation(path => path === '/me' ? data(role)
        : path.includes('/members?') ? data(roster)
        : path.startsWith('/projects/') ? data({ project: { ...summary, status }, items: [application], next_cursor: null })
        : path.startsWith('/me/applications?project_id=') ? data({ items: current ? [current] : [], next_cursor: null })
        : data({ items: [application], next_cursor: null }));
}
function view(path: string, value = project) {
    return render(<MemoryRouter initialEntries={[path]}><Routes>
        <Route path="/projects/:projectId" element={<ProjectParticipation project={value} />} />
        <Route path="/projects/:projectId/applications" element={<ProjectApplicants />} />
        <Route path="/projects/:projectId/team" element={<ProjectTeam />} />
        <Route path="/my-teams" element={<h1>My teams</h1>} />
        <Route path="/my-applications" element={<MyApplications />} />
    </Routes></MemoryRouter>);
}
beforeEach(() => { vi.resetAllMocks(); HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; }); HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) { this.open = false; }); setup(); });
afterEach(cleanup);
it('submits only the message and refreshes the saved application', async () => {
    mocks.post.mockResolvedValue(application);
    view('/projects/project-a');
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Application message (optional)'), '  I can help  ');
    await user.click(screen.getByRole('button', { name: 'Apply to project' }));
    expect(mocks.post).toHaveBeenCalledExactlyOnceWith('/projects/project-a/applications', { message: 'I can help' }, expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('keeps a failed application message and prevents duplicate submissions', async () => {
    let reject!: (error: Error) => void;
    mocks.post.mockReturnValue(new Promise((_, no) => { reject = no; }));
    view('/projects/project-a');
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Application message (optional)'), 'Keep this message');
    await user.click(screen.getByRole('button', { name: 'Apply to project' }));
    const button = screen.getByRole('button', { name: 'Submitting…' });
    expect(button.closest('fieldset')?.disabled).toBe(true);
    await user.click(button);
    expect(mocks.post).toHaveBeenCalledTimes(1);
    await act(async () => reject(new ApiError(409, 'The project team is full')));
    expect(screen.getByRole('alert').textContent).toContain('full');
    expect((screen.getByLabelText('Application message (optional)') as HTMLTextAreaElement).value).toBe('Keep this message');
    expect(mocks.reload).not.toHaveBeenCalled();
});
it('offers withdrawal for a pending application even if the project has closed', async () => {
    setup({ current: application }); mocks.patch.mockResolvedValue({ ...application, status: 'withdrawn' });
    view('/projects/project-a', { ...project, status: 'in_progress' });
    await userEvent.setup().click(screen.getByRole('button', { name: 'Withdraw application' }));
    expect(mocks.patch).toHaveBeenCalledWith('/applications/app-a/withdraw', {}, expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('offers resubmission only for a withdrawn application on an open project', () => {
    setup({ current: { ...application, status: 'withdrawn' } });
    view('/projects/project-a');
    expect(screen.getByRole('button', { name: 'Resubmit application' })).toBeTruthy();
    expect((screen.getByLabelText('Application message (optional)') as HTMLTextAreaElement).value).toBe('I can help');
});
it.each(['accepted','rejected'] as const)('keeps %s history without offering reapplication', status => {
    setup({ current: { ...application, status } }); view('/projects/project-a');
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.queryByRole('button', { name: /Apply|Resubmit/ })).toBeNull();
});
it.each([{ ...project, member_count: 2 }, { ...project, status: 'completed' as const }])('does not offer submission on a full or closed project', value => {
    view('/projects/project-a', value);
    expect(screen.queryByRole('textbox')).toBeNull();
});
it('shows retry instead of an application form when loading fails', async () => {
    mocks.resource.mockReturnValue({ error: new Error('Unavailable'), loading: false, reload: mocks.reload });
    view('/projects/project-a');
    expect(screen.queryByRole('textbox')).toBeNull();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry application' }));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('sends owner acceptance and refreshes after success', async () => {
    mocks.patch.mockResolvedValue({ ...application, status: 'accepted' });
    view('/projects/project-a/applications');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Accept Noah' }));
    expect(mocks.patch).toHaveBeenCalledExactlyOnceWith('/applications/app-a/decision', { status: 'accepted' }, expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('shows a capacity conflict without reporting acceptance or losing the applicant', async () => {
    mocks.patch.mockRejectedValue(new ApiError(409, 'The project team is full'));
    view('/projects/project-a/applications');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Accept Noah' }));
    expect(screen.getByRole('alert').textContent).toContain('team is full');
    expect(screen.getByText('I can help')).toBeTruthy();
    expect(mocks.reload).not.toHaveBeenCalled();
});
it('disables acceptance for a closed project and all decisions for an archive', () => {
    setup({ status: 'archived' }); view('/projects/project-a/applications');
    expect(screen.getByRole('button', { name: 'Accept Noah' }).closest('fieldset')?.disabled).toBe(true);
    expect(screen.getByRole('button', { name: 'Reject Noah' }).closest('fieldset')?.disabled).toBe(true);
});
it('shows owner removal controls and protects the owner membership', async () => {
    setup({ role: { ...me, id: owner.id } }); mocks.remove.mockResolvedValue({ removed: true });
    view('/projects/project-a/team');
    expect(screen.getByText('2 members / 2 capacity · Includes the owner.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Remove Maya' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Leave team' })).toBeNull();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Remove Noah' }));
    expect(mocks.remove).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Confirm removal' }));
    expect(mocks.remove).toHaveBeenCalledWith('/projects/project-a/members/applicant', expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('lets a member confirm leaving and returns to current teams', async () => {
    mocks.remove.mockResolvedValue({ removed: true }); view('/projects/project-a/team');
    expect(screen.queryByRole('button', { name: 'Remove Maya' })).toBeNull();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Leave team' }));
    expect(mocks.remove).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Confirm leave' }));
    expect(await screen.findByRole('heading', { name: 'My teams' })).toBeTruthy();
});
it('keeps archived roster read only', () => {
    setup({ roster: { ...team, project: { ...summary, status: 'archived' } } });
    view('/projects/project-a/team');
    expect(screen.queryByRole('button', { name: /Leave|Remove/ })).toBeNull();
});
it('does not render a roster when the server denies membership', () => {
    mocks.resource.mockImplementation(path => path === '/me' ? data(me) : { error: new ApiError(403, 'Denied'), loading: false, reload: mocks.reload });
    view('/projects/project-a/team');
    expect(screen.getByRole('alert').textContent).toContain('restricted to the owner');
    expect(screen.queryByText('Noah')).toBeNull();
});
it('filters own application history and resets pagination', async () => {
    view('/my-applications');
    await userEvent.setup().selectOptions(screen.getByRole('combobox', { name: 'Application status' }), 'accepted');
    expect(mocks.resource).toHaveBeenLastCalledWith('/me/applications?limit=10&status=accepted');
});
it('ignores a late response after leaving the screen', async () => {
    let finish!: (value: unknown) => void;
    mocks.post.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    const rendered = view('/projects/project-a');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Apply to project' }));
    rendered.unmount();
    expect(mocks.post.mock.calls[0][2].aborted).toBe(true);
    await act(async () => finish(application));
    await waitFor(() => expect(mocks.reload).not.toHaveBeenCalled());
});

it('cancels leaving without changing membership', async () => {
    view('/projects/project-a/team');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Leave team' }));
    await userEvent.setup().click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(mocks.remove).not.toHaveBeenCalled();
});
it('requires confirmation before a final rejection and keeps failures retryable', async () => {
    mocks.patch.mockRejectedValue(new Error('Could not save decision'));
    view('/projects/project-a/applications');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reject Noah' }));
    expect(mocks.patch).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Confirm rejection' }));
    expect(mocks.patch).toHaveBeenCalledWith('/applications/app-a/decision', { status: 'rejected' }, expect.any(AbortSignal));
    expect(screen.getByRole('dialog').textContent).toContain('Could not save decision');
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(mocks.reload).not.toHaveBeenCalled();
});
it('sends accepted application history to current teams rather than a possibly revoked roster', () => {
    mocks.resource.mockReturnValue(data({ items: [{ ...application, status: 'accepted', project: { ...summary, status: 'in_progress' } }], next_cursor: null }));
    view('/my-applications');
    expect(screen.getByRole('link', { name: 'View your current teams' }).getAttribute('href')).toBe('/my-teams');
    expect(screen.queryByRole('link', { name: 'View team' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'View project' })).toBeNull();
});
