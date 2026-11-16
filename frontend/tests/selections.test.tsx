// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProfileSelections } from '../src/ProfileSelections';
import type { Me } from '../src/types';

const mocks = vi.hoisted(() => ({ put: vi.fn(), resource: vi.fn(), reload: vi.fn() }));
vi.mock('../src/api', () => ({ api: { put: mocks.put }, loadCatalog: vi.fn() }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
const skills = [{ id: 'python-id', name: 'python' }, { id: 'react-id', name: 'react' }];
const interests = [{ id: 'robotics-id', name: 'robotics' }];
const me: Me = { id: 'user-a', role: 'student', faculty_verified_at: null, profile: null,
    skills: [skills[0]], interests: [] };
beforeEach(() => {
    vi.resetAllMocks();
    mocks.resource.mockImplementation(path => ({
        data: { items: path === '/skills' ? skills : interests, next_cursor: null },
        loading: false, reload: mocks.reload,
    }));
});
afterEach(cleanup);
it('loads the saved profile selections as checked boxes', () => {
    render(<ProfileSelections me={me} />);
    expect((screen.getByRole('checkbox', { name: 'python' }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByRole('checkbox', { name: 'react' }) as HTMLInputElement).checked).toBe(false);
});
it('replaces skills using IDs and displays the confirmed server selection', async () => {
    mocks.put.mockResolvedValue({ skills: [skills[1]] });
    render(<ProfileSelections me={me} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'python' }));
    await user.click(screen.getByRole('checkbox', { name: 'react' }));
    await user.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(mocks.put).toHaveBeenCalledExactlyOnceWith('/me/skills', { skill_ids: ['react-id'] });
    expect(screen.getByText('Skills saved.')).toBeTruthy();
    expect((screen.getByRole('checkbox', { name: 'react' }) as HTMLInputElement).checked).toBe(true);
});
it('clears a selection by saving an empty array', async () => {
    mocks.put.mockResolvedValue({ skills: [] });
    render(<ProfileSelections me={me} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'python' }));
    await user.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(mocks.put).toHaveBeenCalledExactlyOnceWith('/me/skills', { skill_ids: [] });
});
it('saves interests separately without resetting unsaved skill choices', async () => {
    mocks.put.mockResolvedValue({ interests });
    render(<ProfileSelections me={me} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'react' }));
    await user.click(screen.getByRole('checkbox', { name: 'robotics' }));
    await user.click(screen.getByRole('button', { name: 'Save interests' }));
    expect(mocks.put).toHaveBeenCalledExactlyOnceWith('/me/interests', { interest_ids: ['robotics-id'] });
    expect((screen.getByRole('checkbox', { name: 'react' }) as HTMLInputElement).checked).toBe(true);
});
it('retains choices and shows failed saves without reporting success', async () => {
    mocks.put.mockRejectedValue(new Error('Unknown skill IDs'));
    render(<ProfileSelections me={me} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'react' }));
    await user.click(screen.getByRole('button', { name: 'Save skills' }));
    expect(screen.getByRole('alert').textContent).toContain('Unknown skill IDs');
    expect((screen.getByRole('checkbox', { name: 'react' }) as HTMLInputElement).checked).toBe(true);
    expect(screen.queryByText('Skills saved.')).toBeNull();
});
it('disables saving if the catalogs fail to load and offers retry', async () => {
    mocks.resource.mockReturnValue({ error: new Error('Unavailable'), loading: false, reload: mocks.reload });
    render(<ProfileSelections me={me} />);
    const user = userEvent.setup();
    const save = screen.getByRole('button', { name: 'Save skills' });
    expect(save.closest('fieldset')?.disabled).toBe(true);
    await user.click(save);
    expect(mocks.put).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Retry skills' }));
    expect(mocks.reload).toHaveBeenCalledTimes(1);
});
it('prevents repeated clicks during a selection save', async () => {
    let finish!: (value: unknown) => void;
    mocks.put.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    render(<ProfileSelections me={me} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Save skills' }));
    const pending = screen.getByRole('button', { name: 'Saving skills…' });
    expect(pending.closest('fieldset')?.disabled).toBe(true);
    await user.click(pending);
    expect(mocks.put).toHaveBeenCalledTimes(1);
    finish({ skills });
    await waitFor(() => expect(screen.getByText('Skills saved.')).toBeTruthy());
});
