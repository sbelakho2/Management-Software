'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  LayoutGrid,
  Users,
  Target,
  BarChart3,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

export default function NewObeyaBoardPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: 'Obeya Board Created',
      description: 'Your new digital obeya board has been successfully initialized.',
    });
    router.push('/obeya');
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">New Obeya Board</h1>
            <p className="text-muted-foreground">Create a centralized management board for your team</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? 'Creating...' : 'Create Board'}
          </Button>
        </div>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Board Configuration</CardTitle>
            <CardDescription>Basic details and ownership of the board</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Label htmlFor="name">Board Name</Label>
                <Input id="name" placeholder="e.g. Operations Tier 2 Board" className="mt-1.5" />
              </div>
              <div>
                <Label htmlFor="team">Department / Team</Label>
                <Select>
                  <SelectTrigger id="team" className="mt-1.5">
                    <SelectValue placeholder="Select team" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ops">Operations</SelectItem>
                    <SelectItem value="eng">Engineering</SelectItem>
                    <SelectItem value="quality">Quality</SelectItem>
                    <SelectItem value="sales">Sales</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="owner">Board Owner</Label>
                <Input id="owner" placeholder="Search users..." className="mt-1.5" />
              </div>
            </div>
            <div>
              <Label htmlFor="desc">Description</Label>
              <Textarea id="desc" placeholder="Purpose and scope of this board..." className="mt-1.5" rows={3} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sections & Modules</CardTitle>
            <CardDescription>Select which SQDCP modules to enable</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { id: 'safety', label: 'Safety (S)', color: 'bg-green-100 text-green-700' },
                { id: 'quality', label: 'Quality (Q)', color: 'bg-blue-100 text-blue-700' },
                { id: 'delivery', label: 'Delivery (D)', color: 'bg-yellow-100 text-yellow-700' },
                { id: 'cost', label: 'Cost (C)', color: 'bg-red-100 text-red-700' },
                { id: 'people', label: 'People (P)', color: 'bg-purple-100 text-purple-700' },
                { id: 'exceptions', label: 'Exceptions Log', color: 'bg-slate-100 text-slate-700' },
              ].map((module) => (
                <div key={module.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <div className={cn("w-2 h-8 rounded-full", module.color.split(' ')[0])} />
                    <span className="font-medium text-sm">{module.label}</span>
                  </div>
                  <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
