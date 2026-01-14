'use client';

import * as React from 'react';
import { useProjectManagementStore, type Project, type ProjectStatus, type ProjectType } from '@/stores/project-management-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Globe, Lock, Save, Trash2, AlertTriangle } from 'lucide-react';

interface ProjectSettingsProps {
  projectId: string;
}

export function ProjectSettings({ projectId }: ProjectSettingsProps) {
  const { toast } = useToast();
  const { selectedProject, updateProject } = useProjectManagementStore();
  
  const [form, setForm] = React.useState<Partial<Project>>({});
  const [isSaving, setIsSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (selectedProject) {
      setForm(selectedProject);
    }
  }, [selectedProject]);

  if (!selectedProject) return null;

  const handleSave = async () => {
    setIsSubmitting(true);
    try {
      await updateProject(selectedProject.id, form);
      toast({ title: 'Settings saved', description: 'Project settings have been updated.' });
    } catch (error) {
      toast({ title: 'Failed to save', description: 'There was an error saving your changes.', variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
          <CardDescription>Update project name, description, and visibility.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="name">Project Name</Label>
            <Input 
              id="name" 
              value={form.name || ''} 
              onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea 
              id="description" 
              value={form.description || ''} 
              onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
              rows={4}
            />
          </div>
          <div className="flex items-center justify-between rounded-md border p-4">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                {form.is_private ? <Lock className="h-4 w-4" /> : <Globe className="h-4 w-4" />}
                <Label>Private Project</Label>
              </div>
              <p className="text-sm text-muted-foreground">
                Private projects are only visible to members.
              </p>
            </div>
            <Switch 
              checked={form.is_private || false}
              onCheckedChange={(checked) => setForm(f => ({ ...f, is_private: checked }))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Module Settings</CardTitle>
          <CardDescription>Enable or disable specific project modules.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div className="space-y-0.5">
              <Label>Sprints</Label>
              <p className="text-sm text-muted-foreground">Time-boxed iterations for work.</p>
            </div>
            <Switch 
              checked={form.enable_sprints !== false}
              onCheckedChange={(checked) => setForm(f => ({ ...f, enable_sprints: checked }))}
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <div className="space-y-0.5">
              <Label>Issues</Label>
              <p className="text-sm text-muted-foreground">Bug tracking and improvements.</p>
            </div>
            <Switch 
              checked={form.enable_issues !== false}
              onCheckedChange={(checked) => setForm(f => ({ ...f, enable_issues: checked }))}
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <div className="space-y-0.5">
              <Label>Wiki</Label>
              <p className="text-sm text-muted-foreground">Project documentation and knowledge base.</p>
            </div>
            <Switch 
              checked={form.enable_wiki !== false}
              onCheckedChange={(checked) => setForm(f => ({ ...f, enable_wiki: checked }))}
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-4">
        <Button onClick={handleSave} disabled={isSaving}>
          <Save className="h-4 w-4 mr-2" /> {isSaving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>

      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" /> Danger Zone
          </CardTitle>
          <CardDescription>Permanent actions that cannot be undone.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Delete Project</p>
              <p className="text-sm text-muted-foreground">This will permanently delete the project and all its data.</p>
            </div>
            <Button variant="destructive">
              <Trash2 className="h-4 w-4 mr-2" /> Delete Project
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
