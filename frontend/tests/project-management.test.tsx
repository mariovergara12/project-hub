// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectForm, ProjectEditor } from '../src/ProjectEditor';
import { ProjectDetail } from '../src/ProjectDetail';
import { MyProjects } from '../src/MyProjects';
import type { Me, Project } from '../src/types';

const mocks = vi.hoisted(() => ({ post: vi.fn(), patch: vi.fn(), resource: vi.fn(), reload: vi.fn() }));
vi.mock('../src/api', () => ({ api: { post: mocks.post, patch: mocks.patch }, loadCatalog: vi.fn() }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
vi.mock('../src/Collaboration', () => ({ ProjectParticipation: () => null }));
vi.mock('../src/AccountAccess', () => ({ AccountAccess: () => null }));
const me: Me = { id: 'owner', role: 'student', faculty_verified_at: null, profile: null, skills: [], interests: [] };
const project: Project = {
    id: 'project-a', title: 'Saved draft', description: 'Saved description', project_type: 'student_project',
    status: 'draft', weekly_hours: 0, minimum_experience_years: null, max_members: 2, member_count: 1,
    owner: { id: me.id, display_name: 'Owner', role: 'student', faculty_verified: false },
    skills: [{ id: 'python', name: 'python', required: false }], interests: [{ id: 'robotics', name: 'robotics' }],
    created_at: '', updated_at: '',
};
beforeEach(() => {
    vi.resetAllMocks();
    mocks.resource.mockImplementation(path => ({ data: path === '/me' ? me : path === '/skills'
        ? { items: [{ id: 'python', name: 'python' }] } : path === '/interests'
        ? { items: [{ id: 'robotics', name: 'robotics' }] } : path.startsWith('/me/projects')
        ? { items: [project], next_cursor: null } : project, loading: false, reload: mocks.reload }));
});
afterEach(cleanup);
function form(initial?: Project) {
    return render(<MemoryRouter><Routes><Route path="/" element={<ProjectForm me={me} initial={initial} />} />
        <Route path="/my-projects" element={<p>Cancelled editing</p>} /><Route path="/projects/:id" element={<p>Saved project preview</p>} /></Routes></MemoryRouter>);
}
it('creates a draft with zero hours, catalog IDs and required/optional requirements', async () => {
    mocks.post.mockResolvedValue(project);
    form();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Title'), 'New draft');
    await user.type(screen.getByLabelText('Description'), 'Build together');
    await user.type(screen.getByLabelText('Weekly hours'), '0');
    await user.selectOptions(screen.getByRole('combobox', { name: 'python requirement' }), 'optional');
    await user.click(screen.getByRole('checkbox', { name: 'robotics' }));
    await user.click(screen.getByRole('button', { name: 'Create draft' }));
    expect(mocks.post).toHaveBeenCalledExactlyOnceWith('/projects', {
        title: 'New draft', description: 'Build together', project_type: 'student_project', weekly_hours: 0,
        minimum_experience_years: null, max_members: null,
        skills: [{ skill_id: 'python', required: false }], interest_ids: ['robotics'],
    }, expect.any(AbortSignal));
    expect(await screen.findByText('Saved project preview')).toBeTruthy();
    expect(mocks.patch).not.toHaveBeenCalled();
});
it('preserves edits after a failed save and clears requirements using empty arrays', async () => {
    mocks.patch.mockRejectedValue(new Error('Capacity conflict'));
    form(project);
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText('Title'));
    await user.type(screen.getByLabelText('Title'), 'Keep my edit');
    await user.selectOptions(screen.getByRole('combobox', { name: 'python requirement' }), '');
    await user.click(screen.getByRole('checkbox', { name: 'robotics' }));
    await user.click(screen.getByRole('button', { name: 'Save project' }));
    expect(screen.getByRole('alert').textContent).toContain('Capacity conflict');
    expect((screen.getByLabelText('Title') as HTMLInputElement).value).toBe('Keep my edit');
    expect(mocks.patch).toHaveBeenCalledWith('/projects/project-a', expect.objectContaining({
        skills: [], interest_ids: [], weekly_hours: 0, title: 'Keep my edit',
    }), expect.any(AbortSignal));
});
it('prevents duplicate submissions while saving', async () => {
    let finish!: (value: Project) => void;
    mocks.patch.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    form(project);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Save project' }));
    const button = screen.getByRole('button', { name: 'Saving project…' });
    expect(button.closest('fieldset')?.disabled).toBe(true);
    await user.click(button);
    expect(mocks.patch).toHaveBeenCalledTimes(1);
    finish(project);
    await screen.findByText('Saved project preview');
});
it('does not offer research creation to unverified accounts', () => {
    form();
    expect(screen.queryByRole('option', { name: 'Research opportunity' })).toBeNull();
});
it('blocks editing another owner project and archived projects', () => {
    mocks.resource.mockImplementation(path => ({ data: path === '/me' ? me : { ...project, owner: { ...project.owner, id: 'other' } }, loading: false }));
    const view = render(<MemoryRouter initialEntries={['/projects/project-a/edit']}><Routes>
        <Route path="/projects/:projectId/edit" element={<ProjectEditor />} /></Routes></MemoryRouter>);
    expect(screen.getByRole('alert').textContent).toContain('Only the project owner');
    expect(screen.queryByRole('button', { name: 'Save project' })).toBeNull();
    view.unmount();
    mocks.resource.mockImplementation(path => ({ data: path === '/me' ? me : { ...project, status: 'archived' }, loading: false }));
    render(<MemoryRouter initialEntries={['/projects/project-a/edit']}><Routes>
        <Route path="/projects/:projectId/edit" element={<ProjectEditor />} /></Routes></MemoryRouter>);
    expect(screen.getByText(/Archived projects are read-only/)).toBeTruthy();
});
it('shows owner draft preview and publishes through the status endpoint', async () => {
    mocks.patch.mockResolvedValue({ ...project, status: 'open' });
    render(<MemoryRouter><ProjectDetail /></MemoryRouter>);
    expect(screen.getByText(/private draft preview/)).toBeTruthy();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Publish project' }));
    expect(mocks.patch).toHaveBeenCalledExactlyOnceWith('/projects/project-a/status', { status: 'open' }, expect.any(AbortSignal));
    await waitFor(() => expect(mocks.reload).toHaveBeenCalledOnce());
});
it('hides management controls from other accounts', () => {
    mocks.resource.mockImplementation(path => ({ data: path === '/me' ? { ...me, id: 'other' } : project, loading: false }));
    render(<MemoryRouter><ProjectDetail /></MemoryRouter>);
    expect(screen.queryByRole('region', { name: 'Manage project' })).toBeNull();
});
it('lists owned drafts and changes the status filter', async () => {
    render(<MemoryRouter><MyProjects /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Saved draft' }).getAttribute('href')).toBe('/projects/project-a');
    await userEvent.setup().selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'archived');
    expect(mocks.resource).toHaveBeenLastCalledWith('/me/projects?limit=10&status=archived');
});

it('does not navigate away from the next page when a cancelled save finishes late', async () => {
    let finish!: (value: Project) => void;
    mocks.post.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    form();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Title'), 'Draft');
    await user.type(screen.getByLabelText('Description'), 'New draft description');
    await user.click(screen.getByRole('button', { name: 'Create draft' }));
    await user.click(screen.getByRole('link', { name: 'Cancel' }));
    expect(mocks.post.mock.calls[0][2].aborted).toBe(true);
    finish(project);
    await waitFor(() => expect(screen.getByText('Cancelled editing')).toBeTruthy());
    expect(screen.queryByText('Saved project preview')).toBeNull();
});
