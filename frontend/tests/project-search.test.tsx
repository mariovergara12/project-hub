// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectSearch } from '../src/ProjectSearch';
import type { Project } from '../src/types';

const mocks = vi.hoisted(() => ({ resource: vi.fn(), reload: vi.fn(), search: vi.fn() }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
const base: Project = {
    id: 'library', title: 'Campus library', description: 'Build together', status: 'open',
    project_type: 'student_project', weekly_hours: 4, minimum_experience_years: null,
    max_members: 5, member_count: 1, owner: { id: 'owner', display_name: 'Maya', role: 'student', faculty_verified: false },
    skills: [], interests: [], created_at: '', updated_at: '',
};
const projects = [base, { ...base, id: 'robotics', title: 'Robotics lab' }];
beforeEach(() => {
    vi.resetAllMocks();
    mocks.resource.mockReturnValue({ data: { items: projects, next_cursor: null }, loading: false, reload: mocks.reload });
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })));
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });
function show() {
    return render(<MemoryRouter><Routes><Route path="/" element={<ProjectSearch onSearch={mocks.search} />} /><Route path="/projects/:id" element={<h1>Opened project</h1>} /></Routes></MemoryRouter>);
}

it('opens suggestions and navigates to a keyboard-selected project', async () => {
    show();
    const user = userEvent.setup();
    const input = screen.getByRole('combobox', { name: 'Search projects' });
    await user.click(input);
    expect(screen.getAllByRole('option')).toHaveLength(2);
    await user.keyboard('{ArrowDown}');
    expect(input.getAttribute('aria-activedescendant')).toContain('library');
    await user.keyboard('{Enter}');
    expect(await screen.findByRole('heading', { name: 'Opened project' })).toBeTruthy();
    expect(mocks.search).not.toHaveBeenCalled();
});

it('submits a trimmed query without replacing it with a rotating title', async () => {
    show();
    const user = userEvent.setup();
    const input = screen.getByRole('combobox', { name: 'Search projects' });
    await user.type(input, '  robotics  ');
    await user.click(screen.getByRole('button', { name: 'Search all projects' }));
    expect(mocks.search).toHaveBeenCalledExactlyOnceWith('robotics');
    expect((input as HTMLInputElement).value).toBe('  robotics  ');
    expect(input.getAttribute('aria-expanded')).toBe('false');
});

it('rotates examples only while idle and never changes the input value', () => {
    vi.useFakeTimers();
    show();
    const input = screen.getByRole('combobox', { name: 'Search projects' });
    expect(screen.getByText('Campus library')).toBeTruthy();
    act(() => vi.advanceTimersByTime(3600));
    expect(screen.getByText('Robotics lab')).toBeTruthy();
    fireEvent.focus(input);
    act(() => vi.advanceTimersByTime(10800));
    fireEvent.blur(input);
    expect(screen.getByText('Robotics lab', { selector: '.rotating-project' })).toBeTruthy();
    expect((input as HTMLInputElement).value).toBe('');
});

it('respects reduced motion for the project-title suggestions', () => {
    vi.useFakeTimers();
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
    show();
    act(() => vi.advanceTimersByTime(7200));
    expect(screen.getByText('Campus library')).toBeTruthy();
    expect(screen.queryByText('Robotics lab')).toBeNull();
});

it('offers a retry when suggestion loading fails', async () => {
    mocks.resource.mockReturnValue({ error: new Error('Unavailable'), loading: false, reload: mocks.reload });
    show();
    const user = userEvent.setup();
    await user.click(screen.getByRole('combobox', { name: 'Search projects' }));
    expect(screen.getByRole('alert').textContent).toContain('Could not load projects');
    await user.click(screen.getByRole('button', { name: 'Retry search' }));
    expect(mocks.reload).toHaveBeenCalledOnce();
    expect(screen.queryByRole('option')).toBeNull();
});
