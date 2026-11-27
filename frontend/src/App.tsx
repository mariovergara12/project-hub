import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './AuthProvider';
import { RequireAuth } from './RequireAuth';
import { AppShell } from './AppShell';
import { PageLoading } from './ui';
import './App.css';

const Login = lazy(() => import('./Login').then(module => ({ default: module.Login })));
const ProjectHub = lazy(() => import('./Coursepage').then(module => ({ default: module.ProjectHub })));
const Profile = lazy(() => import('./Profile').then(module => ({ default: module.Profile })));
const ProjectDetail = lazy(() => import('./ProjectDetail').then(module => ({ default: module.ProjectDetail })));
const ProjectEditor = lazy(() => import('./ProjectEditor').then(module => ({ default: module.ProjectEditor })));
const MyProjects = lazy(() => import('./MyProjects').then(module => ({ default: module.MyProjects })));
const ProjectMilestones = lazy(() => import('./Milestones').then(module => ({ default: module.ProjectMilestones })));
const MyTeams = lazy(() => import('./MyTeams').then(module => ({ default: module.MyTeams })));
const ForgotPassword = lazy(() => import('./AccountRecovery').then(module => ({ default: module.ForgotPassword })));
const ResetPassword = lazy(() => import('./AccountRecovery').then(module => ({ default: module.ResetPassword })));
const AuthCallback = lazy(() => import('./AccountRecovery').then(module => ({ default: module.AuthCallback })));
const AccountWelcome = lazy(() => import('./AccountRecovery').then(module => ({ default: module.AccountWelcome })));

const MyApplications = lazy(() => import('./Collaboration').then(module => ({ default: module.MyApplications })));
const ProjectApplicants = lazy(() => import('./Collaboration').then(module => ({ default: module.ProjectApplicants })));
const ProjectTeam = lazy(() => import('./Collaboration').then(module => ({ default: module.ProjectTeam })));

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Suspense fallback={<PageLoading />}>
                    <Routes>
                        <Route path='/' element={<Login/>}/>
                        <Route path='/forgot-password' element={<ForgotPassword/>}/>
                        <Route path='/reset-password' element={<ResetPassword/>}/>
                        <Route path='/auth/callback' element={<AuthCallback/>}/>
                        <Route element={<RequireAuth/>}>
                          <Route path='/welcome' element={<AccountWelcome/>}/>
                          <Route element={<AppShell/>}>
                            <Route path='/main' element={<ProjectHub/>}/>
                            <Route path='/profile' element={<Profile/>}/>
                            <Route path='/my-applications' element={<MyApplications/>}/>
                            <Route path='/my-teams' element={<MyTeams/>}/>
                            <Route path='/projects/:projectId/applications' element={<ProjectApplicants/>}/>
                            <Route path='/projects/:projectId/milestones' element={<ProjectMilestones/>}/>
                            <Route path='/projects/:projectId/team' element={<ProjectTeam/>}/>
                            <Route path='/my-projects' element={<MyProjects/>}/>
                            <Route path='/projects/new' element={<ProjectEditor/>}/>
                            <Route path='/projects/:projectId/edit' element={<ProjectEditor/>}/>
                            <Route path='/projects/:projectId' element={<ProjectDetail/>}/>
                          </Route>
                        </Route>
                    </Routes>
                </Suspense>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
