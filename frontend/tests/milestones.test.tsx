// @vitest-environment jsdom
import { act, cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectMilestones } from '../src/Milestones';
import { ApiError } from '../src/lib/api-client';
import type { Milestone, MilestonePage } from '../src/types';

const mocks = vi.hoisted(() => ({ resource: vi.fn(), reload: vi.fn(), post: vi.fn(), patch: vi.fn(), remove: vi.fn() }));
vi.mock('../src/api', () => ({ api: { post: mocks.post, patch: mocks.patch, delete: mocks.remove } }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
const item: Milestone = { id: 'milestone-a', project_id: 'project-a', title: 'First prototype', description: 'Sketch the first screen', due_date: '2026-11-29', status: 'todo', created_at: '', updated_at: '' };
const data: MilestonePage = { project: { id: 'project-a', title: 'Campus map', owner_id: 'owner', status: 'open' }, items: [item], next_cursor: null, progress: { total: 4, todo: 2, in_progress: 1, completed: 1 } };
function show(path = '/projects/project-a/milestones') {
    return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/projects/:projectId/milestones" element={<ProjectMilestones />} /><Route path="/my-teams" element={<h1>My teams route</h1>} /></Routes></MemoryRouter>);
}
beforeEach(() => {
    vi.resetAllMocks();
    mocks.resource.mockReturnValue({ data, loading: false, reload: mocks.reload });
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) { this.open = false; });
});
afterEach(cleanup);
it('shows overall progress and keeps date-only deadlines intact', () => {
    show();
    expect(screen.getByText('1 of 4 milestones completed')).toBeTruthy();
    expect(screen.getByRole('progressbar', { name: 'Milestones completed' }).getAttribute('value')).toBe('1');
    expect(screen.getByRole('progressbar').getAttribute('max')).toBe('4');
    expect(document.querySelector('time')?.dateTime).toBe('2026-11-29');
    expect(screen.getByText('25%')).toBeTruthy();
});
it('creates a milestone with trimmed values and null optional fields', async () => {
    mocks.post.mockResolvedValue(item); show(); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Add milestone' }));
    await user.type(screen.getByLabelText('Title'), '  Plan the demo  ');
    await user.click(screen.getByRole('button', { name: 'Create milestone' }));
    expect(mocks.post).toHaveBeenCalledExactlyOnceWith('/projects/project-a/milestones', { title: 'Plan the demo', description: null, due_date: null, status: 'todo' }, expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
    expect(screen.getByRole('status').textContent).toContain('Milestone created');
    expect(screen.queryByLabelText('Title')).toBeNull();
});
it('preserves an edit after failure and can clear its optional date and description', async () => {
    mocks.patch.mockRejectedValue(new Error('Could not save milestone')); show(); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Edit First prototype' }));
    await user.clear(screen.getByLabelText('Description (optional)'));
    await user.clear(screen.getByLabelText('Due date (optional)'));
    await user.clear(screen.getByLabelText('Title'));
    await user.type(screen.getByLabelText('Title'), 'Keep my work');
    await user.click(screen.getByRole('button', { name: 'Save milestone' }));
    expect(mocks.patch).toHaveBeenCalledWith('/milestones/milestone-a', { title: 'Keep my work', description: null, due_date: null, status: 'todo' }, expect.any(AbortSignal));
    expect(screen.getByRole('alert').textContent).toContain('Could not save');
    expect((screen.getByLabelText('Title') as HTMLInputElement).value).toBe('Keep my work');
    expect(mocks.reload).not.toHaveBeenCalled();
});
it('prevents duplicate creates and blocks other changes while a form is open', async () => {
    let finish!: (value: unknown) => void;
    mocks.post.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    show(); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Add milestone' }));
    await user.type(screen.getByLabelText('Title'), 'Demo');
    expect((screen.getByLabelText('Milestone status') as HTMLSelectElement).disabled).toBe(true);
    expect((screen.getByRole('button', { name: 'Delete First prototype' }) as HTMLButtonElement).disabled).toBe(true);
    await user.click(screen.getByRole('button', { name: 'Create milestone' }));
    await user.click(screen.getByRole('button', { name: 'Saving…' }));
    expect(mocks.post).toHaveBeenCalledTimes(1);
    await act(async () => finish(item));
});
it('updates status and reloads progress after a successful save', async () => {
    mocks.patch.mockResolvedValue({ ...item, status: 'completed' }); show();
    await userEvent.setup().selectOptions(screen.getByLabelText('Status for First prototype'), 'completed');
    expect(mocks.patch).toHaveBeenCalledExactlyOnceWith('/milestones/milestone-a', { status: 'completed' }, expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('requires delete confirmation, supports cancellation, and handles 204 success', async () => {
    mocks.remove.mockResolvedValue(undefined); show(); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Delete First prototype' }));
    expect(mocks.remove).not.toHaveBeenCalled();
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Delete First prototype' }));
    await user.click(screen.getByRole('button', { name: 'Delete milestone' }));
    expect(mocks.remove).toHaveBeenCalledExactlyOnceWith('/milestones/milestone-a', expect.any(AbortSignal));
    expect(mocks.reload).toHaveBeenCalledOnce();
    expect(screen.queryByRole('dialog')).toBeNull();
});
it('keeps a failed deletion inside its confirmation with retry available', async () => {
    mocks.remove.mockRejectedValue(new Error('Project is now read-only')); show(); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Delete First prototype' }));
    await user.click(screen.getByRole('button', { name: 'Delete milestone' }));
    expect(within(screen.getByRole('dialog')).getByRole('alert').textContent).toContain('read-only');
    expect(mocks.reload).not.toHaveBeenCalled();
});
it.each(['completed', 'archived'] as const)('renders a %s project without edit or delete controls', status => {
    mocks.resource.mockReturnValue({ data: { ...data, project: { ...data.project, status } }, loading: false }); show();
    expect(screen.getByText(`This project is ${status}. Milestones are read-only.`)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Add|Edit|Delete/ })).toBeNull();
    expect(screen.queryByLabelText('Status for First prototype')).toBeNull();
});
it('preserves filters while paging and resets the cursor when changing status', async () => {
    mocks.resource.mockReturnValue({ data: { ...data, next_cursor: 'next' }, loading: false });
    show('/projects/project-a/milestones?status=todo'); const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    expect(mocks.resource).toHaveBeenLastCalledWith('/projects/project-a/milestones?limit=12&status=todo&cursor=next');
    await user.selectOptions(screen.getByLabelText('Milestone status'), 'completed');
    expect(mocks.resource).toHaveBeenLastCalledWith('/projects/project-a/milestones?limit=12&status=completed');
    expect(screen.getByText('1 of 4 milestones completed')).toBeTruthy();
});
it('shows a private-team error without controls or stale milestone content', async () => {
    mocks.resource.mockReturnValue({ error: new ApiError(404, 'Unavailable'), loading: false, reload: mocks.reload }); show();
    expect(screen.queryByText('First prototype')).toBeNull();
    expect(screen.getByRole('alert').textContent).toContain('current team members');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry milestones' }));
    expect(mocks.reload).toHaveBeenCalledOnce();
});
it('handles an empty project with zero progress', () => {
    mocks.resource.mockReturnValue({ data: { ...data, items: [], progress: { total: 0, todo: 0, in_progress: 0, completed: 0 } }, loading: false }); show();
    expect(screen.getByRole('heading', { name: 'Start with a clear next step' })).toBeTruthy();
    expect(screen.getByText('0%')).toBeTruthy();
});
it('aborts a pending status update when navigating to another project', async () => {
    mocks.patch.mockReturnValue(new Promise(() => {}));
    const view = show();
    await userEvent.setup().selectOptions(screen.getByLabelText('Status for First prototype'), 'completed');
    const signal = mocks.patch.mock.calls[0][2];
    view.unmount();
    expect(signal.aborted).toBe(true);
});
