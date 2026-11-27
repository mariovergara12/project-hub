// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ProjectHub } from '../src/Coursepage';

const mocks = vi.hoisted(() => ({ resource: vi.fn() }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
vi.mock('../src/api', () => ({ loadCatalog: vi.fn() }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('keeps search and filters distinct when rendering and clearing the default route', async () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {});
    mocks.resource.mockImplementation(path => ({ data: path === '/projects/recommended' ? { items: [], missing_fields: ['skills', 'interests', 'availability_hours', 'experience_years'] } : { items: [], next_cursor: null }, loading: false, reload: vi.fn() }));
    render(<MemoryRouter><ProjectHub /></MemoryRouter>);
    const user = userEvent.setup();
    expect(screen.getByRole('heading', { name: 'Find a project. Make it happen.' })).toBeTruthy();
    await user.type(screen.getByRole('combobox', { name: 'Search projects' }), 'robotics');
    await user.click(screen.getByRole('button', { name: 'Search all projects' }));
    await user.click(within(screen.getByRole('region', { name: 'Projects' })).getByRole('button', { name: 'Clear filters', exact: true }));
    expect((screen.getByRole('combobox', { name: 'Search projects' }) as HTMLInputElement).value).toBe('');
    expect(errors).not.toHaveBeenCalled();
});

it.each(['q=react', 'project_type=student_project', 'status=open', 'skill_id=react', 'interest_id=community', 'cursor=next'])('focuses on filtered discovery without loading recommendations for %s', query => {
    mocks.resource.mockClear();
    mocks.resource.mockReturnValue({ data: { items: [], next_cursor: null }, loading: false });
    render(<MemoryRouter initialEntries={[`/main?${query}`]}><ProjectHub /></MemoryRouter>);
    expect(screen.queryByRole('region', { name: 'Recommended for you' })).toBeNull();
    expect(mocks.resource.mock.calls.some(([path]) => path === '/projects/recommended')).toBe(false);
    expect(screen.getByRole('region', { name: 'Projects' })).toBeTruthy();
});
