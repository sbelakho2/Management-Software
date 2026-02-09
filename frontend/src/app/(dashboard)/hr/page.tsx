'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { 
  Users, 
  UserPlus, 
  Calendar, 
  Award,
  Clock,
  AlertCircle,
  TrendingUp,
  FileText,
  GraduationCap,
  Building2,
  Search,
  MoreHorizontal,
  Mail,
  MapPin,
  Briefcase,
  Filter,
  Download,
  Loader2,
  Trash2,
  Edit,
  Plus,
  Eye,
  Star,
  CheckCircle,
  XCircle,
  ChevronRight,
  DollarSign,
  Phone,
  CalendarDays,
  FileCheck,
  UserCheck,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { AmbientStatus } from '@/components/ui/stat-card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';
import { hasPageAccess, HR_ROLES } from '@/lib/page-access';
import { useAuthStore, useHRStore } from '@/stores';
import { PageGuard } from '@/components/layout/page-guard';
import type { UserRole, EmployeeProfile, HRJobOpening, HRJobApplication, HRLeaveRequest } from '@/types';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { Pagination } from '@/components/ui/pagination';
import { z } from 'zod';

// --- Zod schemas for form validation ---
const employeeSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  email: z.string().min(1, 'Email is required').email('Invalid email format'),
  department: z.string().optional(),
  job_title: z.string().optional(),
  jurisdiction: z.string().default('TN'),
  status: z.enum(['active', 'inactive', 'on_leave', 'terminated']).default('active'),
});

const jobOpeningSchema = z.object({
  title: z.string().min(1, 'Job title is required'),
  department: z.string().min(1, 'Department is required'),
  description: z.string().optional(),
  employment_type: z.string().default('full_time'),
  status: z.string().default('open'),
});

const leaveRequestSchema = z.object({
  employee_id: z.string().min(1, 'Employee is required'),
  leave_type: z.string().min(1, 'Leave type is required'),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
  reason: z.string().optional(),
});

type FieldErrors = Record<string, string>;

// Application status pipeline stages
const APPLICATION_STAGES = ['received', 'screening', 'interview', 'offer', 'hired', 'rejected'] as const;
type ApplicationStatus = typeof APPLICATION_STAGES[number];

const statusColors: Record<ApplicationStatus, string> = {
  received: 'bg-rams-steel/20 text-rams-steel border-rams-steel/30',
  screening: 'bg-blue-500/20 text-blue-400 border-blue-400/30',
  interview: 'bg-purple-500/20 text-purple-400 border-purple-400/30',
  offer: 'bg-rams-orange/20 text-rams-orange border-rams-orange/30',
  hired: 'bg-rams-green/20 text-rams-green border-rams-green/30',
  rejected: 'bg-rams-red/20 text-rams-red border-rams-red/30',
};

const leaveStatusColors: Record<string, string> = {
  pending: 'bg-rams-orange/20 text-rams-orange border-rams-orange/30',
  approved: 'bg-rams-green/20 text-rams-green border-rams-green/30',
  rejected: 'bg-rams-red/20 text-rams-red border-rams-red/30',
};

export default function HRDashboard() {
  const { t } = useI18n();
  const { user } = useAuthStore();
  const { toast } = useToast();
  const { 
    stats, 
    headcount, 
    expiringCerts, 
    employees,
    jobOpenings,
    applications,
    leaveRequests,
    loading,
    error,
    fetchStats, 
    fetchHeadcount, 
    fetchExpiringCerts,
    fetchEmployees,
    createEmployee,
    deleteEmployee,
    fetchJobOpenings,
    createJobOpening,
    updateJobOpening,
    deleteJobOpening,
    fetchApplications,
    createApplication,
    updateApplicationStatus,
    fetchLeaveRequests,
    createLeaveRequest,
    approveLeaveRequest,
    rejectLeaveRequest,
  } = useHRStore();

  const [activeTab, setActiveTab] = React.useState('overview');
  const [searchTerm, setSearchTerm] = React.useState('');
  const [jobSearchTerm, setJobSearchTerm] = React.useState('');

  // Pagination state (#289)
  const PAGE_SIZE = 12;
  const [employeePage, setEmployeePage] = React.useState(1);
  const [jobPage, setJobPage] = React.useState(1);
  const [leavePage, setLeavePage] = React.useState(1);

  // Reset page when search changes
  React.useEffect(() => { setEmployeePage(1); }, [searchTerm]);
  React.useEffect(() => { setJobPage(1); }, [jobSearchTerm]);
  
  // Dialog states
  const [showAddDialog, setShowAddDialog] = React.useState(false);
  const [showJobDialog, setShowJobDialog] = React.useState(false);
  const [showApplicationDialog, setShowApplicationDialog] = React.useState(false);
  const [showLeaveDialog, setShowLeaveDialog] = React.useState(false);
  const [showApplicationDetailDialog, setShowApplicationDetailDialog] = React.useState(false);
  
  const [deleteConfirmation, setDeleteConfirmation] = React.useState<{
    isOpen: boolean;
    type: 'employee' | 'job' | 'application' | 'leave';
    id: string;
    title: string;
    description: string;
  }>({
    isOpen: false,
    type: 'employee',
    id: '',
    title: '',
    description: '',
  });

  const [formError, setFormError] = React.useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});

  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [selectedApplication, setSelectedApplication] = React.useState<HRJobApplication | null>(null);
  const [selectedJobForApplication, setSelectedJobForApplication] = React.useState<string>('');

  // Form States
  const [newEmployee, setNewEmployee] = React.useState<Partial<EmployeeProfile>>({
    first_name: '',
    last_name: '',
    email: '',
    department: '',
    job_title: '',
    jurisdiction: 'TN',
    status: 'active',
  });

  const [newJob, setNewJob] = React.useState<Partial<HRJobOpening>>({
    title: '',
    department: '',
    description: '',
    requirements: '',
    location: '',
    employment_type: 'full_time',
    salary_range_min: undefined,
    salary_range_max: undefined,
    status: 'open',
  });

  const [newApplication, setNewApplication] = React.useState<Partial<HRJobApplication>>({
    job_opening_id: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    resume_url: '',
    cover_letter: '',
    status: 'received',
  });

  const [newLeaveRequest, setNewLeaveRequest] = React.useState<Partial<HRLeaveRequest>>({
    employee_id: '',
    leave_type: 'pto',
    start_date: '',
    end_date: '',
    reason: '',
    status: 'pending',
  });

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  React.useEffect(() => {
    fetchStats();
    fetchHeadcount();
    fetchExpiringCerts();
    fetchEmployees();
    fetchJobOpenings();
    fetchApplications();
    fetchLeaveRequests();
  }, [fetchStats, fetchHeadcount, fetchExpiringCerts, fetchEmployees, fetchJobOpenings, fetchApplications, fetchLeaveRequests]);

  // Filtered lists
  const filteredEmployees = React.useMemo(() => {
    if (!searchTerm) return employees;
    return employees.filter(emp => 
      emp.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.job_title?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [employees, searchTerm]);

  // Paginated slices (#289)
  const employeeTotalPages = Math.max(1, Math.ceil(filteredEmployees.length / PAGE_SIZE));
  const paginatedEmployees = filteredEmployees.slice((employeePage - 1) * PAGE_SIZE, employeePage * PAGE_SIZE);

  const filteredJobOpenings = React.useMemo(() => {
    if (!jobSearchTerm) return jobOpenings;
    return jobOpenings.filter(job => 
      job.title.toLowerCase().includes(jobSearchTerm.toLowerCase()) ||
      job.department?.toLowerCase().includes(jobSearchTerm.toLowerCase())
    );
  }, [jobOpenings, jobSearchTerm]);

  const jobTotalPages = Math.max(1, Math.ceil(filteredJobOpenings.length / PAGE_SIZE));
  const paginatedJobOpenings = filteredJobOpenings.slice((jobPage - 1) * PAGE_SIZE, jobPage * PAGE_SIZE);

  const pendingLeaveRequests = React.useMemo(() => {
    return leaveRequests.filter(req => req.status === 'pending');
  }, [leaveRequests]);

  const leaveTotalPages = Math.max(1, Math.ceil(leaveRequests.length / PAGE_SIZE));
  const paginatedLeaveRequests = leaveRequests.slice((leavePage - 1) * PAGE_SIZE, leavePage * PAGE_SIZE);

  // Group applications by status for pipeline view
  const applicationsByStatus = React.useMemo(() => {
    const grouped: Record<ApplicationStatus, HRJobApplication[]> = {
      received: [],
      screening: [],
      interview: [],
      offer: [],
      hired: [],
      rejected: [],
    };
    
    applications.forEach(app => {
      if (grouped[app.status]) {
        grouped[app.status].push(app);
      } else {
        // Fallback for unknown status
        grouped.received.push(app);
      }
    });
    
    return grouped;
  }, [applications]);

  const handleCreateEmployee = async () => {
    setFormError(null);
    setFieldErrors({});
    const result = employeeSchema.safeParse(newEmployee);
    if (!result.success) {
      const errs: FieldErrors = {};
      result.error.issues.forEach(issue => {
        const key = issue.path[0] as string;
        if (!errs[key]) errs[key] = issue.message;
      });
      setFieldErrors(errs);
      setFormError(Object.values(errs).join('. '));
      return;
    }
    setIsSubmitting(true);
    try {
      await createEmployee(newEmployee);
      toast({ title: "Success", description: "Employee created successfully" });
      setShowAddDialog(false);
      setNewEmployee({ first_name: '', last_name: '', email: '', department: '', job_title: '', jurisdiction: 'TN', status: 'active' });
    } catch (error: any) {
      setFormError(error.message || "Failed to create employee");
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmDeleteEmployee = (id: string) => {
    setDeleteConfirmation({
      isOpen: true,
      type: 'employee',
      id,
      title: 'Terminate Employee Record',
      description: 'Are you sure you want to remove this employee record? This action cannot be undone and will revoke all system access.'
    });
  };

  const handleCreateJobOpening = async () => {
    setFormError(null);
    if (!newJob.title || !newJob.department) {
      setFormError("Title and department are required");
      return;
    }
    setIsSubmitting(true);
    try {
      await createJobOpening(newJob);
      toast({ title: "Success", description: "Job opening created" });
      setShowJobDialog(false);
      setNewJob({ title: '', department: '', description: '', requirements: '', location: '', employment_type: 'full_time', status: 'open' });
    } catch (error: any) {
      setFormError(error.message || "Failed to create job opening");
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmDeleteJob = (id: string) => {
    setDeleteConfirmation({
      isOpen: true,
      type: 'job',
      id,
      title: 'Delete Job Opening',
      description: 'Are you sure you want to delete this job opening? Associated applications will not be deleted but will be unlinked.'
    });
  };

  const handleCreateApplication = async () => {
    setFormError(null);
    if (!newApplication.job_opening_id || !newApplication.first_name || !newApplication.last_name || !newApplication.email) {
      setFormError("Please fill in all required fields");
      return;
    }
    setIsSubmitting(true);
    try {
      await createApplication(newApplication);
      toast({ title: "Success", description: "Application submitted" });
      setShowApplicationDialog(false);
      setNewApplication({ job_opening_id: '', first_name: '', last_name: '', email: '', phone: '', resume_url: '', cover_letter: '', status: 'received' });
    } catch (error: any) {
      setFormError(error.message || "Failed to submit application");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateApplicationStatus = async (id: string, status: ApplicationStatus) => {
    try {
      await updateApplicationStatus(id, status);
      toast({ title: "Success", description: `Application moved to ${status}` });
      if (selectedApplication?.id === id) {
        setSelectedApplication({ ...selectedApplication, status });
      }
    } catch (error) {
      // Inline error not applicable here as it's a direct action, toast is fine for this one or persistent alert
      toast({ title: "Error", description: "Failed to update application status", variant: "destructive" });
    }
  };

  const handleCreateLeaveRequest = async () => {
    setFormError(null);
    if (!newLeaveRequest.employee_id || !newLeaveRequest.start_date || !newLeaveRequest.end_date) {
      setFormError("Please fill in all required fields");
      return;
    }
    setIsSubmitting(true);
    try {
      await createLeaveRequest(newLeaveRequest);
      toast({ title: "Success", description: "Leave request submitted" });
      setShowLeaveDialog(false);
      setNewLeaveRequest({ employee_id: '', leave_type: 'pto', start_date: '', end_date: '', reason: '', status: 'pending' });
    } catch (error: any) {
      setFormError(error.message || "Failed to submit leave request");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApproveLeave = async (id: string) => {
    try {
      await approveLeaveRequest(id);
      toast({ title: "Success", description: "Leave request approved" });
    } catch (error) {
      toast({ title: "Error", description: "Failed to approve leave request", variant: "destructive" });
    }
  };

  const handleRejectLeave = async (id: string) => {
    try {
      await rejectLeaveRequest(id);
      toast({ title: "Success", description: "Leave request rejected" });
    } catch (error) {
      toast({ title: "Error", description: "Failed to reject leave request", variant: "destructive" });
    }
  };

  const handleConfirmDelete = async () => {
    try {
      if (deleteConfirmation.type === 'employee') {
        await deleteEmployee(deleteConfirmation.id);
        toast({ title: "Success", description: "Employee record terminated" });
      } else if (deleteConfirmation.type === 'job') {
        await deleteJobOpening(deleteConfirmation.id);
        toast({ title: "Success", description: "Job opening deleted" });
      }
      setDeleteConfirmation(prev => ({ ...prev, isOpen: false }));
    } catch (error) {
      toast({ title: "Error", description: "Failed to perform deletion", variant: "destructive" });
    }
  };

  if (loading && !stats && employees.length === 0) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-rams-orange" />
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground animate-pulse">
          Initializing HR Protocols...
        </p>
      </div>
    );
  }

  return (
    <PageGuard requiredRoles={HR_ROLES}>
      <div className="space-y-4 page-fade-in pb-12" data-testid="hr-dashboard">
        {/* Error state */}
        {error && (
          <div className="rounded-rams-sm border border-destructive/50 bg-destructive/10 p-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="text-sm font-bold text-destructive">Error loading HR data</p>
                <p className="text-xs text-muted-foreground">{error}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => { fetchStats(); fetchEmployees(); }}>
              Retry
            </Button>
          </div>
        )}

        {/* Header */}
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('pages.hr.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('pages.hr.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>{t('pages.hr.station')}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            {hasPageAccess('/training', userRoles) && (
              <Button variant="outline" size="sm" className="rounded-rams-sm border-rams-line hidden md:flex" asChild>
                <Link href="/training">
                  <GraduationCap className="h-3.5 w-3.5 mr-2" />
                  {t('pages.hr.trainingMatrix') || 'Training Matrix'}
                </Link>
              </Button>
            )}
            {hasPageAccess('/hr/add', userRoles) && (
              <Button 
                size="sm" 
                className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]"
                onClick={() => {
                  setActiveTab('employees');
                  setShowAddDialog(true);
                }}
              >
                <UserPlus className="h-3.5 w-3.5 mr-2" />
                {t('pages.hr.initializePersonnel') || 'Initialize Personnel'}
              </Button>
            )}
          </div>
        </div>

        {/* System Status & Tabs */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <div className="flex items-center justify-between mb-6">
                <TabsList className="bg-rams-panel/50 border border-rams-line p-1">
                  <TabsTrigger value="overview" className="uppercase text-[10px] font-bold tracking-wider data-[state=active]:bg-rams-orange data-[state=active]:text-black">Overview</TabsTrigger>
                  <TabsTrigger value="employees" className="uppercase text-[10px] font-bold tracking-wider data-[state=active]:bg-rams-orange data-[state=active]:text-black">Employees</TabsTrigger>
                  <TabsTrigger value="recruitment" className="uppercase text-[10px] font-bold tracking-wider data-[state=active]:bg-rams-orange data-[state=active]:text-black">Recruitment</TabsTrigger>
                  <TabsTrigger value="leave" className="uppercase text-[10px] font-bold tracking-wider data-[state=active]:bg-rams-orange data-[state=active]:text-black">Leave</TabsTrigger>
                </TabsList>
                <AmbientStatus status="operational" label={t('pages.hr.hrSystemsOnline')} />
              </div>

              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-4 animate-in slide-in-from-left-2 duration-300">
                {/* Stats Grid */}
                <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
                  <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                    <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.headcountNode') || 'Headcount Node'}</p>
                    <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.total_employees || 0}</div>
                    <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2 flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" /> +{stats?.new_hires_this_month || 0} {t('pages.hr.thisCycle')}
                    </p>
                  </div>
                  <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                    <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.opportunityPulse') || 'Opportunity Pulse'}</p>
                    <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats?.open_positions || jobOpenings.filter(j => j.status === 'open').length}</div>
                    <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">{t('pages.hr.activeRecruitment')}</p>
                  </div>
                  <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                    <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.capacitySync') || 'Capacity Sync'}</p>
                    <div className="text-3xl font-mono font-bold tracking-tight text-rams-steel tabular-nums">{stats?.pending_time_off || pendingLeaveRequests.length}</div>
                    <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.hr.pendingRequests')}</p>
                  </div>
                  <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                    <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.thresholdBreaches') || 'Threshold Breaches'}</p>
                    <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", (stats?.expiring_certifications || 0) > 5 ? "text-rams-red" : "text-foreground/90")}>
                      {stats?.expiring_certifications || 0}
                    </div>
                    <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.hr.complianceGates')}</p>
                  </div>
                </div>

                {/* Main Content */}
                <div className="grid gap-4 lg:grid-cols-3">
                  {/* Pending Time Off */}
                  <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
                    <CardHeader className="bg-rams-panel/20 border-b border-rams-line text-foreground">
                      <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                        <Clock className="h-4 w-4 text-rams-orange" />
                        {t('pages.hr.strategicAvailability') || 'Strategic Availability'}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 space-y-0.5 bg-rams-line">
                      {pendingLeaveRequests.length === 0 ? (
                        <div className="p-6 text-center text-muted-foreground bg-rams-module">
                          <Calendar className="h-8 w-8 mx-auto opacity-30 mb-2" />
                          <p className="text-xs font-mono uppercase">No pending requests</p>
                        </div>
                      ) : (
                        pendingLeaveRequests.slice(0, 3).map((request) => {
                          const emp = employees.find(e => e.id === request.employee_id);
                          return (
                            <div
                              key={request.id}
                              className="flex items-center justify-between p-3 bg-rams-module hover:bg-rams-panel transition-none group"
                            >
                              <div className="flex items-center gap-3">
                                <Avatar className="h-8 w-8 rounded-rams-sm border border-rams-line">
                                  <AvatarFallback>{emp ? `${emp.first_name[0]}${emp.last_name[0]}` : '?'}</AvatarFallback>
                                </Avatar>
                                <div>
                                  <p className="font-sans font-black text-[10px] uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">
                                    {emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown'}
                                  </p>
                                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                                    {request.start_date} - {request.end_date}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-1">
                                <Badge variant="outline" className="rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-5 bg-transparent border-rams-line mr-2">
                                  {request.leave_type}
                                </Badge>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-rams-green hover:bg-rams-green/10" onClick={() => handleApproveLeave(request.id)}>
                                      <CheckCircle className="h-3.5 w-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Approve</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-rams-red hover:bg-rams-red/10" onClick={() => handleRejectLeave(request.id)}>
                                      <XCircle className="h-3.5 w-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Reject</TooltipContent>
                                </Tooltip>
                              </div>
                            </div>
                          );
                        })
                      )}
                      <div className="p-3 bg-rams-module flex gap-2">
                        <Button size="sm" className="flex-1 rounded-rams-sm bg-rams-orange text-black font-black uppercase text-[9px] h-8 transition-none" onClick={() => setActiveTab('leave')}>
                          {t('pages.hr.reviewAll') || 'Review All'}
                        </Button>
                        <Button size="sm" variant="outline" className="flex-1 rounded-rams-sm border-rams-line text-[9px] font-black uppercase h-8 transition-none" onClick={() => setShowLeaveDialog(true)}>
                          New Request
                        </Button>
                      </div>
                    </CardContent>
                  </Card>


                  {/* Expiring Certifications */}
                  <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
                    <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                      <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-rams-red" />
                        {t('pages.hr.intelligenceThresholds') || 'Intelligence Thresholds'}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 space-y-0.5 bg-rams-line">
                      {expiringCerts.length === 0 ? (
                        <div className="p-6 text-center text-muted-foreground bg-rams-module">
                          <Award className="h-8 w-8 mx-auto opacity-30 mb-2" />
                          <p className="text-xs font-mono uppercase">No expiring certifications</p>
                        </div>
                      ) : (
                        expiringCerts.map((cert) => (
                          <div
                            key={cert.id}
                            className="flex items-center justify-between p-3 bg-rams-module hover:bg-rams-red/5 transition-none group"
                          >
                            <div>
                              <p className="font-sans font-black text-[10px] uppercase tracking-tight text-foreground/80 group-hover:text-rams-red transition-none">{cert.employee}</p>
                              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-rams-red/40 mt-0.5">{cert.cert}</p>
                            </div>
                            <Badge 
                              variant={cert.priority === 'high' ? 'destructive' : 'outline'}
                              className={cn(
                                "rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4",
                                cert.priority === 'medium' ? 'border-rams-orange/20 text-rams-orange bg-rams-orange/5' : 'bg-rams-panel border-rams-line'
                              )}
                            >
                              {cert.expires.toUpperCase()}
                            </Badge>
                          </div>
                        ))
                      )}
                    </CardContent>
                  </Card>

                  {/* Department Headcount */}
                  <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
                    <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                      <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-rams-orange" />
                        {t('pages.hr.nodeDistribution') || 'Node Distribution'}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 bg-rams-module">
                      <div className="space-y-4">
                        {headcount.length === 0 ? (
                          <div className="text-center text-muted-foreground py-6">
                            <Users className="h-8 w-8 mx-auto opacity-30 mb-2" />
                            <p className="text-xs font-mono uppercase">No department data</p>
                          </div>
                        ) : (
                          headcount.map((dept) => (
                            <div key={dept.name} className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{dept.name}</span>
                                <span className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase">{dept.count} {t('pages.hr.nodes')}</span>
                              </div>
                              <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                                <div 
                                  className="h-full bg-rams-orange transition-all duration-1000" 
                                  style={{ width: `${dept.percentage}%` }}
                                />
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              {/* Employees Tab */}
              <TabsContent value="employees" className="space-y-4 animate-in slide-in-from-right-2 duration-300">
                <div className="flex items-center gap-4">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Search personnel..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-9 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono focus-visible:ring-rams-orange"
                    />
                  </div>
                  <div className="flex items-center gap-2 ml-auto">
                    <Button variant="outline" size="sm" className="h-9 rounded-rams-sm border-rams-line">
                      <Filter className="h-3.5 w-3.5 mr-2" />
                      Filter
                    </Button>
                    <Button variant="outline" size="sm" className="h-9 rounded-rams-sm border-rams-line">
                      <Download className="h-3.5 w-3.5 mr-2" />
                      Export
                    </Button>
                  </div>
                </div>

                {filteredEmployees.length === 0 ? (
                  <div className="text-center py-20 border border-dashed border-rams-line rounded-rams-sm bg-rams-module">
                    <Users className="h-12 w-12 mx-auto text-muted-foreground/30 mb-4" />
                    <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest">No personnel records found</h3>
                    <p className="text-xs text-muted-foreground/60 mb-6 font-mono">Initialize personnel to see them here.</p>
                    <Button onClick={() => setShowAddDialog(true)} size="sm" className="rounded-rams-sm bg-rams-orange text-black font-bold text-xs uppercase">
                      Initialize Personnel
                    </Button>
                  </div>
                ) : (
                  <>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {paginatedEmployees.map((emp) => (
                      <div key={emp.id} className="relative rounded-rams-sm border border-rams-line bg-rams-module hover:bg-rams-panel transition-colors group p-4">
                        <div className="flex items-start justify-between mb-3">
                          <Avatar className="h-10 w-10 rounded-rams-sm border border-rams-line">
                            <AvatarFallback className="bg-rams-panel text-rams-orange font-black text-xs">
                              {emp.first_name[0]}{emp.last_name[0]}
                            </AvatarFallback>
                          </Avatar>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-40 rounded-rams-sm border-rams-line bg-rams-module">
                              <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer">
                                <Edit className="h-3 w-3 mr-2" /> Edit Profile
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                className="text-xs uppercase font-bold tracking-wider text-rams-red focus:text-rams-red focus:bg-rams-red/10 cursor-pointer"
                                onClick={() => confirmDeleteEmployee(emp.id)}
                              >
                                <Trash2 className="h-3 w-3 mr-2" /> Terminate
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                        <div className="space-y-0.5 mb-3">
                          <h3 className="font-sans font-black text-xs uppercase tracking-tight truncate">{emp.first_name} {emp.last_name}</h3>
                          <p className="text-[10px] text-muted-foreground font-mono truncate">{emp.job_title || 'Unassigned Role'}</p>
                        </div>
                        <div className="grid gap-1.5 text-[9px] text-muted-foreground font-mono">
                          <div className="flex items-center gap-2">
                            <Briefcase className="h-2.5 w-2.5 opacity-50 shrink-0" />
                            <span className="uppercase tracking-wider truncate">{emp.department || 'No Dept'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <MapPin className="h-2.5 w-2.5 opacity-50 shrink-0" />
                            <span className="uppercase tracking-wider truncate">{emp.site_id || 'Remote'} ({emp.jurisdiction})</span>
                          </div>
                          {emp.email && (
                            <div className="flex items-center gap-2">
                              <Mail className="h-2.5 w-2.5 opacity-50 shrink-0" />
                              <span className="truncate">{emp.email}</span>
                            </div>
                          )}
                        </div>
                        <div className="mt-3 pt-3 border-t border-rams-line flex justify-between items-center">
                          <Badge variant={emp.status === 'active' ? 'default' : 'secondary'} className="text-[8px] uppercase tracking-widest h-4 rounded-none px-1.5 border border-rams-line/50">
                            {emp.status}
                          </Badge>
                          <span className="text-[8px] font-mono text-muted-foreground/50">ID: {emp.id.slice(0, 8)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <Pagination
                    currentPage={employeePage}
                    totalPages={employeeTotalPages}
                    onPageChange={setEmployeePage}
                    totalItems={filteredEmployees.length}
                  />
                  </>
                )}
              </TabsContent>

              {/* Recruitment Tab */}
              <TabsContent value="recruitment" className="space-y-4 animate-in slide-in-from-right-2 duration-300">
                {/* Job Openings Section */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-black uppercase tracking-[0.2em]">Job Openings</h2>
                    <div className="flex items-center gap-3">
                      <div className="relative max-w-xs">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                        <Input
                          placeholder="Search jobs..."
                          value={jobSearchTerm}
                          onChange={(e) => setJobSearchTerm(e.target.value)}
                          className="pl-9 h-9 bg-rams-module border-rams-line rounded-rams-sm w-56 text-xs font-mono"
                        />
                      </div>
                      <Button size="sm" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase text-[10px]" onClick={() => setShowJobDialog(true)}>
                        <Plus className="h-3.5 w-3.5 mr-2" />
                        Post Position
                      </Button>
                    </div>
                  </div>

                  {filteredJobOpenings.length === 0 ? (
                    <div className="text-center py-16 border border-dashed border-rams-line rounded-rams-sm bg-rams-module">
                      <Briefcase className="h-10 w-10 mx-auto text-muted-foreground/30 mb-4" />
                      <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest">No job openings</h3>
                      <p className="text-xs text-muted-foreground/60 mb-4 font-mono">Post a new position to start recruiting.</p>
                      <Button onClick={() => setShowJobDialog(true)} size="sm" className="rounded-rams-sm bg-rams-orange text-black font-bold text-xs uppercase">
                        Post Position
                      </Button>
                    </div>
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {paginatedJobOpenings.map((job) => (
                        <div key={job.id} className="rounded-rams-sm border border-rams-line bg-rams-module hover:bg-rams-panel transition-colors p-4">
                          <div className="flex items-start justify-between mb-3">
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-5",
                                job.status === 'open' ? 'border-rams-green/30 text-rams-green bg-rams-green/10' : 
                                job.status === 'cancelled' ? 'border-rams-red/30 text-rams-red bg-rams-red/10' : 
                                'border-rams-orange/30 text-rams-orange bg-rams-orange/10'
                              )}
                            >
                              {job.status}
                            </Badge>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="w-44 rounded-rams-sm border-rams-line bg-rams-module">
                                <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer" onClick={() => {
                                  setSelectedJobForApplication(job.id);
                                  setNewApplication(prev => ({ ...prev, job_opening_id: job.id }));
                                  setShowApplicationDialog(true);
                                }}>
                                  <UserPlus className="h-3 w-3 mr-2" /> Add Candidate
                                </DropdownMenuItem>
                                <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer">
                                  <Edit className="h-3 w-3 mr-2" /> Edit
                                </DropdownMenuItem>
                                <DropdownMenuSeparator className="bg-rams-line" />
                                <DropdownMenuItem 
                                  className="text-xs uppercase font-bold tracking-wider text-rams-red focus:text-rams-red cursor-pointer"
                                  onClick={() => confirmDeleteJob(job.id)}
                                >
                                  <Trash2 className="h-3 w-3 mr-2" /> Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                          <h3 className="font-sans font-black text-sm uppercase tracking-tight mb-1 line-clamp-1">{job.title}</h3>
                          <p className="text-[10px] text-muted-foreground font-mono mb-3">{job.department}</p>
                          <div className="grid gap-1.5 text-[9px] text-muted-foreground mb-4">
                            {job.location && (
                              <div className="flex items-center gap-2">
                                <MapPin className="h-2.5 w-2.5 opacity-50" />
                                <span className="uppercase tracking-wider">{job.location}</span>
                              </div>
                            )}
                            {job.employment_type && (
                              <div className="flex items-center gap-2">
                                <Clock className="h-2.5 w-2.5 opacity-50" />
                                <span className="uppercase tracking-wider">{job.employment_type}</span>
                              </div>
                            )}
                            {(job.salary_range_min || job.salary_range_max) && (
                              <div className="flex items-center gap-2">
                                <DollarSign className="h-2.5 w-2.5 opacity-50" />
                                <span className="uppercase tracking-wider">
                                  {job.salary_range_min?.toLocaleString()} - {job.salary_range_max?.toLocaleString()}
                                </span>
                              </div>
                            )}
                          </div>
                          <div className="pt-3 border-t border-rams-line flex justify-between items-center">
                            <span className="text-[9px] font-mono text-muted-foreground/50">
                              {job.applications_count || applications.filter(a => a.job_opening_id === job.id).length} candidates
                            </span>
                            <Button variant="ghost" size="sm" className="h-6 text-[9px] uppercase font-bold" onClick={() => {
                              setSelectedJobForApplication(job.id);
                              setNewApplication(prev => ({ ...prev, job_opening_id: job.id }));
                              setShowApplicationDialog(true);
                            }}>
                              Add <ChevronRight className="h-3 w-3 ml-1" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <Pagination currentPage={jobPage} totalPages={jobTotalPages} onPageChange={setJobPage} totalItems={filteredJobOpenings.length} />
                </div>

                {/* Applications Pipeline */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-black uppercase tracking-[0.2em]">Candidate Pipeline</h2>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      <span className="font-mono">{applications.length} Total Candidates</span>
                    </div>
                  </div>

                  {applications.length === 0 ? (
                    <div className="text-center py-12 border border-dashed border-rams-line rounded-rams-sm bg-rams-module">
                      <FileText className="h-8 w-8 mx-auto text-muted-foreground/30 mb-3" />
                      <p className="text-sm text-muted-foreground">No applications yet</p>
                    </div>
                  ) : (
                    <div className="grid gap-3 lg:grid-cols-5" role="region" aria-label="Candidate Pipeline Board">
                      {APPLICATION_STAGES.filter(s => s !== 'rejected').map((stage) => (
                        <div key={stage} className="space-y-2" role="list" aria-label={`${stage} stage — ${applicationsByStatus[stage].length} candidates`}>
                          <div className="flex items-center justify-between px-2">
                            <Badge variant="outline" className={cn("rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-5", statusColors[stage])}>
                              {stage}
                            </Badge>
                            <span className="text-[10px] font-mono text-muted-foreground">{applicationsByStatus[stage].length}</span>
                          </div>
                          <div className="space-y-2 min-h-[200px] p-2 bg-rams-module/50 border border-rams-line rounded-rams-sm">
                            {applicationsByStatus[stage].map((app) => {
                              const job = jobOpenings.find(j => j.id === app.job_opening_id);
                              return (
                                <Card 
                                  key={app.id} 
                                  className="rounded-rams-sm border-rams-line bg-rams-panel hover:border-rams-orange/50 focus-visible:border-rams-orange focus-visible:ring-2 focus-visible:ring-rams-orange/40 focus-visible:outline-none transition-colors cursor-pointer"
                                  tabIndex={0}
                                  role="button"
                                  aria-label={`${app.first_name} ${app.last_name} — ${job?.title || 'Unknown Position'} — ${stage}`}
                                  onClick={() => {
                                    setSelectedApplication(app);
                                    setShowApplicationDetailDialog(true);
                                  }}
                                  onKeyDown={(e: React.KeyboardEvent) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                      e.preventDefault();
                                      setSelectedApplication(app);
                                      setShowApplicationDetailDialog(true);
                                    }
                                  }}
                                >
                                  <CardContent className="p-3">
                                    <p className="font-sans font-bold text-xs truncate">{app.first_name} {app.last_name}</p>
                                    <p className="text-[9px] text-muted-foreground font-mono truncate mt-0.5">{job?.title || 'Unknown Position'}</p>
                                    {app.rating && (
                                      <div className="flex items-center gap-0.5 mt-2">
                                        {[1,2,3,4,5].map(i => (
                                          <Star key={i} className={cn("h-2.5 w-2.5", i <= app.rating! ? "text-rams-orange fill-rams-orange" : "text-muted-foreground/30")} />
                                        ))}
                                      </div>
                                    )}
                                  </CardContent>
                                </Card>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Rejected Applications */}
                  {applicationsByStatus.rejected.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-rams-line">
                      <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2">
                        {applicationsByStatus.rejected.length} Rejected Candidates
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Leave Management Tab */}
              <TabsContent value="leave" className="space-y-6 animate-in slide-in-from-right-2 duration-300">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-black uppercase tracking-[0.2em]">Leave Requests</h2>
                  <Button size="sm" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase text-[10px]" onClick={() => setShowLeaveDialog(true)}>
                    <Plus className="h-3.5 w-3.5 mr-2" />
                    New Request
                  </Button>
                </div>

                {leaveRequests.length === 0 ? (
                  <div className="text-center py-20 border border-dashed border-rams-line rounded-rams-sm bg-rams-module">
                    <Calendar className="h-12 w-12 mx-auto text-muted-foreground/30 mb-4" />
                    <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest">No leave requests</h3>
                    <p className="text-xs text-muted-foreground/60 mb-6 font-mono">Submit a new leave request to get started.</p>
                    <Button onClick={() => setShowLeaveDialog(true)} size="sm" className="rounded-rams-sm bg-rams-orange text-black font-bold text-xs uppercase">
                      Submit Request
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {paginatedLeaveRequests.map((request) => {
                      const emp = employees.find(e => e.id === request.employee_id);
                      return (
                        <div key={request.id} className="rounded-rams-sm border border-rams-line bg-rams-module p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <Avatar className="h-9 w-9 rounded-rams-sm border border-rams-line">
                                <AvatarFallback className="bg-rams-panel font-bold text-xs">
                                  {emp ? `${emp.first_name[0]}${emp.last_name[0]}` : '?'}
                                </AvatarFallback>
                              </Avatar>
                              <div>
                                <p className="font-sans font-black text-xs uppercase tracking-tight">
                                  {emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown Employee'}
                                </p>
                                <div className="flex items-center gap-3 mt-1">
                                  <span className="text-[9px] font-mono text-muted-foreground uppercase">
                                    {request.leave_type}
                                  </span>
                                  <span className="text-[9px] font-mono text-muted-foreground">
                                    <CalendarDays className="h-2.5 w-2.5 inline mr-1 opacity-50" />
                                    {request.start_date} — {request.end_date}
                                  </span>
                                  {request.days_count && (
                                    <span className="text-[9px] font-mono text-muted-foreground">
                                      ({request.days_count} days)
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              <Badge 
                                variant="outline" 
                                className={cn(
                                  "rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-5",
                                  leaveStatusColors[request.status] || 'border-rams-line'
                                )}
                              >
                                {request.status}
                              </Badge>
                              {request.status === 'pending' && (
                                <div className="flex items-center gap-1">
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button 
                                        size="icon" 
                                        variant="ghost" 
                                        className="h-7 w-7 text-rams-green hover:bg-rams-green/10" 
                                        onClick={() => handleApproveLeave(request.id)}
                                      >
                                        <CheckCircle className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Approve</TooltipContent>
                                  </Tooltip>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button 
                                        size="icon" 
                                        variant="ghost" 
                                        className="h-7 w-7 text-rams-red hover:bg-rams-red/10"
                                        onClick={() => handleRejectLeave(request.id)}
                                      >
                                        <XCircle className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Reject</TooltipContent>
                                  </Tooltip>
                                </div>
                              )}
                            </div>
                          </div>
                          {request.reason && (
                            <p className="mt-2 text-[10px] text-muted-foreground pl-12 border-l-2 border-rams-line ml-[18px]">
                              {request.reason}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                <Pagination currentPage={leavePage} totalPages={leaveTotalPages} onPageChange={setLeavePage} totalItems={leaveRequests.length} />
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Add Employee Dialog */}
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogContent className="sm:max-w-[600px] border-rams-line bg-rams-module">
            <DialogHeader>
              <DialogTitle className="uppercase font-black text-lg tracking-tight">Initialize Personnel</DialogTitle>
              <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Create a new employee profile in the HR registry.
              </DialogDescription>
            </DialogHeader>
            {formError && (
              <div className="mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-mono">
                {formError}
              </div>
            )}
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name *</Label>
                  <Input id="firstName" placeholder="E.g. John" value={newEmployee.first_name} onChange={(e) => setNewEmployee(prev => ({ ...prev, first_name: e.target.value }))} className={fieldErrors.first_name ? 'border-red-500' : ''} />
                  {fieldErrors.first_name && <p className="text-[10px] text-red-500 font-mono">{fieldErrors.first_name}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name *</Label>
                  <Input id="lastName" placeholder="E.g. Doe" value={newEmployee.last_name} onChange={(e) => setNewEmployee(prev => ({ ...prev, last_name: e.target.value }))} className={fieldErrors.last_name ? 'border-red-500' : ''} />
                  {fieldErrors.last_name && <p className="text-[10px] text-red-500 font-mono">{fieldErrors.last_name}</p>}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email Address *</Label>
                <Input id="email" type="email" placeholder="john.doe@company.com" value={newEmployee.email} onChange={(e) => setNewEmployee(prev => ({ ...prev, email: e.target.value }))} className={fieldErrors.email ? 'border-red-500' : ''} />
                {fieldErrors.email && <p className="text-[10px] text-red-500 font-mono">{fieldErrors.email}</p>}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="department">Department</Label>
                  <Input id="department" placeholder="E.g. Engineering" value={newEmployee.department} onChange={(e) => setNewEmployee(prev => ({ ...prev, department: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="jobTitle">Job Title</Label>
                  <Input id="jobTitle" placeholder="E.g. Senior Technician" value={newEmployee.job_title} onChange={(e) => setNewEmployee(prev => ({ ...prev, job_title: e.target.value }))} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="jurisdiction">Jurisdiction</Label>
                  <Select value={newEmployee.jurisdiction} onValueChange={(val) => setNewEmployee(prev => ({ ...prev, jurisdiction: val }))}>
                    <SelectTrigger id="jurisdiction"><SelectValue placeholder="Select region" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="TN">Tunisia (TN)</SelectItem>
                      <SelectItem value="MA">Morocco (MA)</SelectItem>
                      <SelectItem value="EG">Egypt (EG)</SelectItem>
                      <SelectItem value="US">United States (US)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-[9px] text-muted-foreground uppercase font-mono tracking-wide">Determines benefits regime</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Initial Status</Label>
                  <Select value={newEmployee.status} onValueChange={(val) => setNewEmployee(prev => ({ ...prev, status: val as any }))}>
                    <SelectTrigger id="status"><SelectValue placeholder="Select status" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="onboarding">Onboarding</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button onClick={handleCreateEmployee} disabled={isSubmitting} className="bg-rams-orange text-black font-bold">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserPlus className="h-4 w-4 mr-2" />}
                Create Profile
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Post Job Dialog */}
        <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
          <DialogContent className="sm:max-w-[600px] border-rams-line bg-rams-module">
            <DialogHeader>
              <DialogTitle className="uppercase font-black text-lg tracking-tight">Post New Position</DialogTitle>
              <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Create a new job opening for recruitment.
              </DialogDescription>
            </DialogHeader>
            {formError && (
              <div className="mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-mono">
                {formError}
              </div>
            )}
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Job Title *</Label>
                  <Input placeholder="E.g. Senior Engineer" value={newJob.title} onChange={(e) => setNewJob(prev => ({ ...prev, title: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>Department *</Label>
                  <Input placeholder="E.g. Engineering" value={newJob.department} onChange={(e) => setNewJob(prev => ({ ...prev, department: e.target.value }))} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Location</Label>
                  <Input placeholder="E.g. Remote, New York" value={newJob.location} onChange={(e) => setNewJob(prev => ({ ...prev, location: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>Employment Type</Label>
                  <Select value={newJob.employment_type} onValueChange={(val) => setNewJob(prev => ({ ...prev, employment_type: val as HRJobOpening['employment_type'] }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="full_time">Full-time</SelectItem>
                      <SelectItem value="part_time">Part-time</SelectItem>
                      <SelectItem value="contract">Contract</SelectItem>
                      <SelectItem value="intern">Internship</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Salary Min</Label>
                  <Input type="number" placeholder="50000" value={newJob.salary_range_min || ''} onChange={(e) => setNewJob(prev => ({ ...prev, salary_range_min: Number(e.target.value) || undefined }))} />
                </div>
                <div className="space-y-2">
                  <Label>Salary Max</Label>
                  <Input type="number" placeholder="80000" value={newJob.salary_range_max || ''} onChange={(e) => setNewJob(prev => ({ ...prev, salary_range_max: Number(e.target.value) || undefined }))} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="Job description..." value={newJob.description} onChange={(e) => setNewJob(prev => ({ ...prev, description: e.target.value }))} rows={3} />
              </div>
              <div className="space-y-2">
                <Label>Requirements</Label>
                <Textarea placeholder="Required skills and qualifications..." value={newJob.requirements} onChange={(e) => setNewJob(prev => ({ ...prev, requirements: e.target.value }))} rows={3} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowJobDialog(false)}>Cancel</Button>
              <Button onClick={handleCreateJobOpening} disabled={isSubmitting} className="bg-rams-orange text-black font-bold">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Briefcase className="h-4 w-4 mr-2" />}
                Post Position
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add Application Dialog */}
        <Dialog open={showApplicationDialog} onOpenChange={setShowApplicationDialog}>
          <DialogContent className="sm:max-w-[500px] border-rams-line bg-rams-module">
            <DialogHeader>
              <DialogTitle className="uppercase font-black text-lg tracking-tight">Add Candidate</DialogTitle>
              <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Submit a new application for the selected position.
              </DialogDescription>
            </DialogHeader>
            {formError && (
              <div className="mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-mono">
                {formError}
              </div>
            )}
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Position *</Label>
                <Select value={newApplication.job_opening_id} onValueChange={(val) => setNewApplication(prev => ({ ...prev, job_opening_id: val }))}>
                  <SelectTrigger><SelectValue placeholder="Select position" /></SelectTrigger>
                  <SelectContent>
                    {jobOpenings.filter(j => j.status === 'open').map(job => (
                      <SelectItem key={job.id} value={job.id}>{job.title} - {job.department}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>First Name *</Label>
                  <Input placeholder="John" value={newApplication.first_name} onChange={(e) => setNewApplication(prev => ({ ...prev, first_name: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>Last Name *</Label>
                  <Input placeholder="Doe" value={newApplication.last_name} onChange={(e) => setNewApplication(prev => ({ ...prev, last_name: e.target.value }))} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Email *</Label>
                <Input type="email" placeholder="john.doe@email.com" value={newApplication.email} onChange={(e) => setNewApplication(prev => ({ ...prev, email: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input placeholder="+1 234 567 8900" value={newApplication.phone} onChange={(e) => setNewApplication(prev => ({ ...prev, phone: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Resume URL</Label>
                <Input placeholder="https://..." value={newApplication.resume_url} onChange={(e) => setNewApplication(prev => ({ ...prev, resume_url: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Cover Letter / Notes</Label>
                <Textarea placeholder="Additional notes..." value={newApplication.cover_letter} onChange={(e) => setNewApplication(prev => ({ ...prev, cover_letter: e.target.value }))} rows={3} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowApplicationDialog(false)}>Cancel</Button>
              <Button onClick={handleCreateApplication} disabled={isSubmitting} className="bg-rams-orange text-black font-bold">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserPlus className="h-4 w-4 mr-2" />}
                Add Candidate
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Application Detail Dialog */}
        <Dialog open={showApplicationDetailDialog} onOpenChange={setShowApplicationDetailDialog}>
          <DialogContent className="sm:max-w-[500px] border-rams-line bg-rams-module">
            <DialogHeader>
              <DialogTitle className="uppercase font-black text-lg tracking-tight">
                {selectedApplication?.first_name} {selectedApplication?.last_name}
              </DialogTitle>
              <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                {jobOpenings.find(j => j.id === selectedApplication?.job_opening_id)?.title || 'Candidate Details'}
              </DialogDescription>
            </DialogHeader>
            {selectedApplication && (
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Email</p>
                    <p className="font-mono">{selectedApplication.email}</p>
                  </div>
                  {selectedApplication.phone && (
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Phone</p>
                      <p className="font-mono">{selectedApplication.phone}</p>
                    </div>
                  )}
                </div>
                {selectedApplication.resume_url && (
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Resume</p>
                    <a href={selectedApplication.resume_url} target="_blank" rel="noopener noreferrer" className="text-rams-orange text-sm hover:underline">
                      View Resume →
                    </a>
                  </div>
                )}
                {selectedApplication.cover_letter && (
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Notes</p>
                    <p className="text-sm text-muted-foreground">{selectedApplication.cover_letter}</p>
                  </div>
                )}
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Move to Stage</p>
                  <div className="flex flex-wrap gap-2">
                    {APPLICATION_STAGES.map(stage => (
                      <Button
                        key={stage}
                        size="sm"
                        variant={selectedApplication.status === stage ? 'default' : 'outline'}
                        className={cn(
                          "rounded-rams-sm text-[9px] uppercase h-7",
                          selectedApplication.status === stage && "bg-rams-orange text-black"
                        )}
                        onClick={() => handleUpdateApplicationStatus(selectedApplication.id, stage)}
                      >
                        {stage}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowApplicationDetailDialog(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Leave Request Dialog */}
        <Dialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
          <DialogContent className="sm:max-w-[500px] border-rams-line bg-rams-module">
            <DialogHeader>
            {formError && (
              <div className="mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-mono">
                {formError}
              </div>
            )}
              <DialogTitle className="uppercase font-black text-lg tracking-tight">Submit Leave Request</DialogTitle>
              <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Request time off for an employee.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Employee *</Label>
                <Select value={newLeaveRequest.employee_id} onValueChange={(val) => setNewLeaveRequest(prev => ({ ...prev, employee_id: val }))}>
                  <SelectTrigger><SelectValue placeholder="Select employee" /></SelectTrigger>
                  <SelectContent>
                    {employees.filter(e => e.status === 'active').map(emp => (
                      <SelectItem key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Leave Type</Label>
                <Select value={newLeaveRequest.leave_type} onValueChange={(val) => setNewLeaveRequest(prev => ({ ...prev, leave_type: val as HRLeaveRequest['leave_type'] }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pto">PTO</SelectItem>
                    <SelectItem value="sick">Sick Leave</SelectItem>
                    <SelectItem value="personal">Personal</SelectItem>
                    <SelectItem value="bereavement">Bereavement</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start Date *</Label>
                  <Input type="date" value={newLeaveRequest.start_date} onChange={(e) => setNewLeaveRequest(prev => ({ ...prev, start_date: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>End Date *</Label>
                  <Input type="date" value={newLeaveRequest.end_date} onChange={(e) => setNewLeaveRequest(prev => ({ ...prev, end_date: e.target.value }))} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Reason</Label>
                <Textarea placeholder="Reason for leave..." value={newLeaveRequest.reason} onChange={(e) => setNewLeaveRequest(prev => ({ ...prev, reason: e.target.value }))} rows={3} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowLeaveDialog(false)}>Cancel</Button>
              <Button onClick={handleCreateLeaveRequest} disabled={isSubmitting} className="bg-rams-orange text-black font-bold">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Calendar className="h-4 w-4 mr-2" />}
                Submit Request
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        {/* Confirmation Dialog */}
        <ConfirmationDialog 
          open={deleteConfirmation.isOpen} 
          onOpenChange={(open) => setDeleteConfirmation(prev => ({ ...prev, isOpen: open }))}
          title={deleteConfirmation.title}
          description={deleteConfirmation.description}
          onConfirm={handleConfirmDelete}
          variant="danger"
          confirmLabel="Delete"
        />
      </div>
    </PageGuard>
  );
}
