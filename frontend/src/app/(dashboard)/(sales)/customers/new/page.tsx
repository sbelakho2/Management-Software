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
import { useI18n } from '@/contexts/i18n-context';

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
  const { t } = useI18n();
  return (
    <div className="border border-rams-line rounded-rams-sm p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground cursor-move" />
          <span className="font-medium">{t('pages.customers.new.contact')} {index + 1}</span>
          {contact.isPrimary && (
            <span className="text-xs bg-rams-orange/10 text-rams-orange px-2 py-0.5 rounded-rams-sm">{t('pages.customers.new.primary')}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!contact.isPrimary && (
            <Button variant="ghost" size="sm" onClick={onSetPrimary}>
              {t('pages.customers.new.setAsPrimary')}
            </Button>
          )}
          <Button variant="ghost" size="icon-sm" onClick={onRemove}>
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-danger" />
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label>{t('pages.customers.new.fullName')}</Label>
          <Input
            value={contact.name}
            onChange={(e) => onChange({ ...contact, name: e.target.value })}
            placeholder={t('pages.customers.new.fullNamePlaceholder')}
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>{t('pages.customers.new.jobTitle')}</Label>
          <Input
            value={contact.title}
            onChange={(e) => onChange({ ...contact, title: e.target.value })}
            placeholder={t('pages.customers.new.jobTitlePlaceholder')}
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>{t('pages.customers.new.email')}</Label>
          <Input
            type="email"
            value={contact.email}
            onChange={(e) => onChange({ ...contact, email: e.target.value })}
            placeholder={t('pages.customers.new.emailPlaceholder')}
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>{t('pages.customers.new.phone')}</Label>
          <Input
            type="tel"
            value={contact.phone}
            onChange={(e) => onChange({ ...contact, phone: e.target.value })}
            placeholder={t('pages.customers.new.phonePlaceholder')}
            className="mt-1.5"
          />
        </div>
      </div>
    </div>
  );
}

import { useCustomersStore } from '@/stores/customers';

export default function CustomerFormPage() {
  const { t } = useI18n();
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
      newErrors.name = t('pages.customers.new.validation.companyNameRequired');
    }
    if (!formData.code.trim()) {
      newErrors.code = t('pages.customers.new.validation.customerCodeRequired');
    }
    if (!formData.industry) {
      newErrors.industry = t('pages.customers.new.validation.industryRequired');
    }
    if (formData.contacts.length === 0) {
      newErrors.contacts = t('pages.customers.new.validation.contactRequired');
    }
    formData.contacts.forEach((contact, index) => {
      if (!contact.name.trim()) {
        newErrors[`contact_${index}_name`] = t('pages.customers.new.validation.contactNameRequired');
      }
      if (!contact.email.trim()) {
        newErrors[`contact_${index}_email`] = t('pages.customers.new.validation.contactEmailRequired');
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      toast({
        variant: 'destructive',
        title: t('pages.customers.new.toast.validationError'),
        description: t('pages.customers.new.toast.fixErrors'),
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
        title: isEditing ? t('pages.customers.new.toast.customerUpdated') : t('pages.customers.new.toast.customerCreated'),
        description: formData.name,
      });
      router.push('/customers');
    } catch {
      toast({
        variant: 'destructive',
        title: t('pages.customers.new.toast.errorSaving'),
        description: t('pages.customers.new.toast.tryAgain'),
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
            <h1 className="text-3xl font-heading font-bold tracking-tight ">
              {isEditing ? t('pages.customers.new.editTitle') : t('pages.customers.new.newTitle')}
            </h1>
            <p className="text-muted-foreground">
              {isEditing ? t('pages.customers.new.editingDescription', { name: formData.name }) : t('pages.customers.new.newDescription')}
            </p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          <Save className="mr-2 h-4 w-4" />
          {isSaving ? t('pages.customers.new.saving') : t('pages.customers.new.saveCustomer')}
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
                {t('pages.customers.new.companyInfo')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Label required>{t('pages.customers.new.companyName')}</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder={t('pages.customers.new.companyNamePlaceholder')}
                    className={cn('mt-1.5', errors.name && 'border-danger')}
                  />
                  {errors.name && <p className="text-sm text-danger mt-1">{errors.name}</p>}
                </div>
                <div>
                  <Label required>{t('pages.customers.new.customerCode')}</Label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      value={formData.code}
                      onChange={(e) => setFormData((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
                      placeholder="ACME-001"
                      className={cn(errors.code && 'border-danger')}
                    />
                    <Button variant="outline" type="button" onClick={generateCode}>
                      {t('pages.customers.new.generate')}
                    </Button>
                  </div>
                  {errors.code && <p className="text-sm text-danger mt-1">{errors.code}</p>}
                </div>
                <div>
                  <Label required>{t('pages.customers.new.industry')}</Label>
                  <Select
                    value={formData.industry}
                    onValueChange={(v) => setFormData((prev) => ({ ...prev, industry: v }))}
                  >
                    <SelectTrigger className={cn('mt-1.5', errors.industry && 'border-danger')}>
                      <SelectValue placeholder={t('pages.customers.new.selectIndustry')} />
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
                  <Label>{t('pages.customers.new.status')}</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(v: 'active' | 'inactive' | 'prospect') => setFormData((prev) => ({ ...prev, status: v }))}
                  >
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="prospect">{t('pages.customers.status.prospect')}</SelectItem>
                      <SelectItem value="active">{t('pages.customers.status.active')}</SelectItem>
                      <SelectItem value="inactive">{t('pages.customers.status.inactive')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{t('pages.customers.new.website')}</Label>
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
                {t('pages.customers.new.address')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{t('pages.customers.new.streetAddress')}</Label>
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
                  <Label>{t('pages.customers.new.city')}</Label>
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
                  <Label>{t('pages.customers.new.stateProvince')}</Label>
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
                  <Label>{t('pages.customers.new.postalCode')}</Label>
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
                  <Label>{t('pages.customers.new.country')}</Label>
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
                  {t('pages.customers.new.contacts')}
                </CardTitle>
                <CardDescription>{t('pages.customers.new.contactsDescription')}</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleAddContact}>
                <Plus className="mr-2 h-4 w-4" />
                {t('pages.customers.new.addContact')}
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
                <div className="text-center py-8 border border-dashed border-rams-line rounded-rams-sm bg-rams-panel/30">
                  <User className="mx-auto h-8 w-8 text-muted-foreground/40" />
                  <p className="mt-2 text-muted-foreground">{t('pages.customers.new.noContacts')}</p>
                  <Button variant="outline" size="sm" className="mt-4" onClick={handleAddContact}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t('pages.customers.new.addFirstContact')}
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
              <CardTitle>{t('pages.customers.new.internalNotes')}</CardTitle>
              <CardDescription>{t('pages.customers.new.internalNotesDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder={t('pages.customers.new.notesPlaceholder')}
                rows={6}
              />
            </CardContent>
          </Card>

          {/* Tips */}
          <Card className="bg-rams-panel border-rams-line">
            <CardContent className="pt-4">
              <h4 className="font-medium mb-2">{t('pages.customers.new.tips')}</h4>
              <ul className="text-sm text-muted-foreground space-y-2">
                <li>• {t('pages.customers.new.tip1')}</li>
                <li>• {t('pages.customers.new.tip2')}</li>
                <li>• {t('pages.customers.new.tip3')}</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
