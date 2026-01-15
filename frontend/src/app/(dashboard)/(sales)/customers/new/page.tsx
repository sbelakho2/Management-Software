'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  Building2,
  User,
  Mail,
  Phone,
  MapPin,
  Globe,
  Plus,
  Trash2,
  GripVertical,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, generateId } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface Contact {
  id: string;
  name: string;
  title: string;
  email: string;
  phone: string;
  isPrimary: boolean;
}

interface CustomerFormData {
  name: string;
  code: string;
  status: 'active' | 'inactive' | 'prospect';
  industry: string;
  website: string;
  address: {
    street: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
  };
  contacts: Contact[];
  notes: string;
}

const industries = [
  'Aerospace',
  'Automotive',
  'Defense',
  'Electronics',
  'Energy',
  'Industrial',
  'Medical',
  'Other',
];

const countries = [
  'USA',
  'Canada',
  'Morocco',
  'United Kingdom',
  'Germany',
  'France',
  'Other',
];

function ContactCard({ 
  contact, 
  index,
  onChange, 
  onRemove,
  onSetPrimary,
}: { 
  contact: Contact; 
  index: number;
  onChange: (contact: Contact) => void;
  onRemove: () => void;
  onSetPrimary: () => void;
}) {
  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground cursor-move" />
          <span className="font-medium">Contact {index + 1}</span>
          {contact.isPrimary && (
            <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">Primary</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!contact.isPrimary && (
            <Button variant="ghost" size="sm" onClick={onSetPrimary}>
              Set as Primary
            </Button>
          )}
          <Button variant="ghost" size="icon-sm" onClick={onRemove}>
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-danger" />
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label>Full Name</Label>
          <Input
            value={contact.name}
            onChange={(e) => onChange({ ...contact, name: e.target.value })}
            placeholder="John Doe"
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>Job Title</Label>
          <Input
            value={contact.title}
            onChange={(e) => onChange({ ...contact, title: e.target.value })}
            placeholder="Procurement Manager"
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>Email</Label>
          <Input
            type="email"
            value={contact.email}
            onChange={(e) => onChange({ ...contact, email: e.target.value })}
            placeholder="john@company.com"
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>Phone</Label>
          <Input
            type="tel"
            value={contact.phone}
            onChange={(e) => onChange({ ...contact, phone: e.target.value })}
            placeholder="+1 (555) 123-4567"
            className="mt-1.5"
          />
        </div>
      </div>
    </div>
  );
}

import { useCustomersStore } from '@/stores/customers';

export default function CustomerFormPage() {
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const { createCustomer, updateCustomer } = useCustomersStore();
  const isEditing = params?.id !== undefined;
  
  const [isLoading, setIsLoading] = React.useState(isEditing);
  const [isSaving, setIsSaving] = React.useState(false);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  
  const [formData, setFormData] = React.useState<CustomerFormData>({
    name: '',
    code: '',
    status: 'prospect',
    industry: '',
    website: '',
    address: {
      street: '',
      city: '',
      state: '',
      postalCode: '',
      country: 'Morocco',
    },
    contacts: [
      {
        id: generateId(),
        name: '',
        title: '',
        email: '',
        phone: '',
        isPrimary: true,
      },
    ],
    notes: '',
  });

  React.useEffect(() => {
    if (isEditing) {
      // Load existing customer data
      const timer = setTimeout(() => {
        setFormData({
          name: 'Aerospace Dynamics Inc.',
          code: 'AERO-001',
          status: 'active',
          industry: 'Aerospace',
          website: 'https://aerospacedynamics.com',
          address: {
            street: '1234 Aviation Blvd',
            city: 'Los Angeles',
            state: 'CA',
            postalCode: '90045',
            country: 'USA',
          },
          contacts: [
            { id: '1', name: 'Michael Roberts', title: 'Procurement Manager', email: 'mroberts@aerospacedynamics.com', phone: '+1 (555) 234-5678', isPrimary: true },
            { id: '2', name: 'Sarah Johnson', title: 'Engineering Lead', email: 'sjohnson@aerospacedynamics.com', phone: '+1 (555) 234-5679', isPrimary: false },
          ],
          notes: 'Preferred customer - always prioritize their RFQs.',
        });
        setIsLoading(false);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isEditing, params?.id]);

  const handleAddContact = () => {
    setFormData((prev) => ({
      ...prev,
      contacts: [
        ...prev.contacts,
        {
          id: generateId(),
          name: '',
          title: '',
          email: '',
          phone: '',
          isPrimary: false,
        },
      ],
    }));
  };

  const handleUpdateContact = (id: string, contact: Contact) => {
    setFormData((prev) => ({
      ...prev,
      contacts: prev.contacts.map((c) => (c.id === id ? contact : c)),
    }));
  };

  const handleRemoveContact = (id: string) => {
    setFormData((prev) => {
      const remaining = prev.contacts.filter((c) => c.id !== id);
      // If we removed the primary contact, make the first remaining one primary
      if (remaining.length > 0 && !remaining.some((c) => c.isPrimary)) {
        remaining[0].isPrimary = true;
      }
      return { ...prev, contacts: remaining };
    });
  };

  const handleSetPrimary = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      contacts: prev.contacts.map((c) => ({ ...c, isPrimary: c.id === id })),
    }));
  };

  const generateCode = () => {
    const prefix = formData.name
      .split(' ')
      .map((w) => w[0]?.toUpperCase() || '')
      .join('')
      .slice(0, 4);
    const suffix = String(Math.floor(Math.random() * 1000)).padStart(3, '0');
    setFormData((prev) => ({ ...prev, code: `${prefix}-${suffix}` }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Company name is required';
    }
    if (!formData.code.trim()) {
      newErrors.code = 'Customer code is required';
    }
    if (!formData.industry) {
      newErrors.industry = 'Industry is required';
    }
    if (formData.contacts.length === 0) {
      newErrors.contacts = 'At least one contact is required';
    }
    formData.contacts.forEach((contact, index) => {
      if (!contact.name.trim()) {
        newErrors[`contact_${index}_name`] = 'Contact name is required';
      }
      if (!contact.email.trim()) {
        newErrors[`contact_${index}_email`] = 'Contact email is required';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      toast({
        variant: 'destructive',
        title: 'Validation Error',
        description: 'Please fix the errors before saving.',
      });
      return;
    }

    setIsSaving(true);
    try {
      if (isEditing) {
        await updateCustomer(params.id as string, formData);
      } else {
        await createCustomer(formData);
      }
      toast({
        title: isEditing ? 'Customer updated' : 'Customer created',
        description: formData.name,
      });
      router.push('/customers');
    } catch {
      toast({
        variant: 'destructive',
        title: 'Error saving customer',
        description: 'Please try again.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-8 w-48" />
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              {isEditing ? 'Edit Customer' : 'New Customer'}
            </h1>
            <p className="text-muted-foreground">
              {isEditing ? `Editing ${formData.name}` : 'Add a new customer to your CRM'}
            </p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          <Save className="mr-2 h-4 w-4" />
          {isSaving ? 'Saving...' : 'Save Customer'}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Company Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Label required>Company Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Acme Corporation"
                    className={cn('mt-1.5', errors.name && 'border-danger')}
                  />
                  {errors.name && <p className="text-sm text-danger mt-1">{errors.name}</p>}
                </div>
                <div>
                  <Label required>Customer Code</Label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      value={formData.code}
                      onChange={(e) => setFormData((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
                      placeholder="ACME-001"
                      className={cn(errors.code && 'border-danger')}
                    />
                    <Button variant="outline" type="button" onClick={generateCode}>
                      Generate
                    </Button>
                  </div>
                  {errors.code && <p className="text-sm text-danger mt-1">{errors.code}</p>}
                </div>
                <div>
                  <Label required>Industry</Label>
                  <Select
                    value={formData.industry}
                    onValueChange={(v) => setFormData((prev) => ({ ...prev, industry: v }))}
                  >
                    <SelectTrigger className={cn('mt-1.5', errors.industry && 'border-danger')}>
                      <SelectValue placeholder="Select industry" />
                    </SelectTrigger>
                    <SelectContent>
                      {industries.map((industry) => (
                        <SelectItem key={industry} value={industry}>{industry}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.industry && <p className="text-sm text-danger mt-1">{errors.industry}</p>}
                </div>
                <div>
                  <Label>Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(v: 'active' | 'inactive' | 'prospect') => setFormData((prev) => ({ ...prev, status: v }))}
                  >
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="prospect">Prospect</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Website</Label>
                  <div className="relative mt-1.5">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      value={formData.website}
                      onChange={(e) => setFormData((prev) => ({ ...prev, website: e.target.value }))}
                      placeholder="https://company.com"
                      className="pl-9"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Address */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Address
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Street Address</Label>
                <Input
                  value={formData.address.street}
                  onChange={(e) => setFormData((prev) => ({ 
                    ...prev, 
                    address: { ...prev.address, street: e.target.value } 
                  }))}
                  placeholder="123 Main Street"
                  className="mt-1.5"
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label>City</Label>
                  <Input
                    value={formData.address.city}
                    onChange={(e) => setFormData((prev) => ({ 
                      ...prev, 
                      address: { ...prev.address, city: e.target.value } 
                    }))}
                    placeholder="City"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label>State / Province</Label>
                  <Input
                    value={formData.address.state}
                    onChange={(e) => setFormData((prev) => ({ 
                      ...prev, 
                      address: { ...prev.address, state: e.target.value } 
                    }))}
                    placeholder="State"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label>Postal Code</Label>
                  <Input
                    value={formData.address.postalCode}
                    onChange={(e) => setFormData((prev) => ({ 
                      ...prev, 
                      address: { ...prev.address, postalCode: e.target.value } 
                    }))}
                    placeholder="12345"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label>Country</Label>
                  <Select
                    value={formData.address.country}
                    onValueChange={(v) => setFormData((prev) => ({ 
                      ...prev, 
                      address: { ...prev.address, country: v } 
                    }))}
                  >
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {countries.map((country) => (
                        <SelectItem key={country} value={country}>{country}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Contacts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Contacts
                </CardTitle>
                <CardDescription>Add contacts for this customer</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleAddContact}>
                <Plus className="mr-2 h-4 w-4" />
                Add Contact
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {errors.contacts && (
                <p className="text-sm text-danger">{errors.contacts}</p>
              )}
              {formData.contacts.map((contact, index) => (
                <ContactCard
                  key={contact.id}
                  contact={contact}
                  index={index}
                  onChange={(updated) => handleUpdateContact(contact.id, updated)}
                  onRemove={() => handleRemoveContact(contact.id)}
                  onSetPrimary={() => handleSetPrimary(contact.id)}
                />
              ))}
              {formData.contacts.length === 0 && (
                <div className="text-center py-8 border-2 border-dashed rounded-lg">
                  <User className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-2 text-muted-foreground">No contacts added</p>
                  <Button variant="outline" size="sm" className="mt-4" onClick={handleAddContact}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add First Contact
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Notes */}
          <Card>
            <CardHeader>
              <CardTitle>Internal Notes</CardTitle>
              <CardDescription>Notes for internal use only</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder="Add notes about this customer..."
                rows={6}
              />
            </CardContent>
          </Card>

          {/* Tips */}
          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <h4 className="font-medium mb-2">Tips</h4>
              <ul className="text-sm text-muted-foreground space-y-2">
                <li>• Customer codes should be unique and easy to remember</li>
                <li>• Mark your main point of contact as Primary</li>
                <li>• Add notes about special requirements or preferences</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
