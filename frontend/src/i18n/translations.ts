export interface TranslationKeys {
  app: {
    name: string;
    description: string;
  };
  auth: {
    login: string;
    register: string;
    logout: string;
    email: string;
    password: string;
    confirmPassword: string;
    tenantName: string;
    forgotPassword: string;
    resetPassword: string;
    loginSuccess: string;
    registerSuccess: string;
    invalidCredentials: string;
  };
  nav: {
    dashboard: string;
    projects: string;
    contracts: string;
    boq: string;
    claims: string;
    procurements: string;
    financial: string;
    reports: string;
    settings: string;
    users: string;
    audit: string;
    notifications: string;
  };
  dashboard: {
    title: string;
    totalProjects: string;
    activeProjects: string;
    totalBudget: string;
    totalEntries: string;
    recentActivity: string;
    projectStatus: string;
    financialOverview: string;
  };
  projects: {
    title: string;
    create: string;
    edit: string;
    delete: string;
    code: string;
    name: string;
    status: string;
    budget: string;
    client: string;
    location: string;
    planning: string;
    active: string;
    completed: string;
    onHold: string;
  };
  contracts: {
    title: string;
    create: string;
    edit: string;
    delete: string;
    number: string;
    projectName: string;
    totalAmount: string;
    status: string;
    draft: string;
    active: string;
    completed: string;
  };
  boq: {
    title: string;
    create: string;
    edit: string;
    items: string;
    itemDescription: string;
    quantity: string;
    unit: string;
    unitPrice: string;
    total: string;
    submit: string;
    approve: string;
  };
  claims: {
    title: string;
    create: string;
    claimNumber: string;
    amount: string;
    status: string;
    pending: string;
    approved: string;
    rejected: string;
    paid: string;
  };
  procurement: {
    title: string;
    create: string;
    edit: string;
    description: string;
    vendor: string;
    amount: string;
    status: string;
    ordered: string;
    received: string;
  };
  financial: {
    title: string;
    accounts: string;
    journalEntries: string;
    createEntry: string;
    debit: string;
    credit: string;
    balance: string;
    accountType: string;
    asset: string;
    liability: string;
    equity: string;
    revenue: string;
    expense: string;
  };
  reports: {
    title: string;
    financialSummary: string;
    profitLoss: string;
    trialBalance: string;
    accountBalances: string;
    export: string;
    exportCSV: string;
    exportExcel: string;
    exportPDF: string;
    dateRange: string;
    startDate: string;
    endDate: string;
  };
  settings: {
    title: string;
    general: string;
    appearance: string;
    language: string;
    notifications: string;
    security: string;
  };
  users: {
    title: string;
    manage: string;
    role: string;
    admin: string;
    manager: string;
    member: string;
    viewer: string;
    addMember: string;
    removeMember: string;
    changeRole: string;
  };
  common: {
    save: string;
    cancel: string;
    delete: string;
    edit: string;
    create: string;
    search: string;
    filter: string;
    export: string;
    import: string;
    loading: string;
    noData: string;
    confirm: string;
    success: string;
    error: string;
    warning: string;
    info: string;
    actions: string;
    status: string;
    date: string;
    total: string;
    back: string;
    next: string;
    previous: string;
    page: string;
    of: string;
    showMore: string;
    showLess: string;
    all: string;
    none: string;
    selectAll: string;
    deselectAll: string;
    required: string;
    optional: string;
    yes: string;
    no: string;
  };
}

export const en: TranslationKeys = {
  app: {
    name: '2TO EOS',
    description: 'Enterprise Resource Planning System',
  },
  auth: {
    login: 'Login',
    register: 'Register',
    logout: 'Logout',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm Password',
    tenantName: 'Organization Name',
    forgotPassword: 'Forgot Password?',
    resetPassword: 'Reset Password',
    loginSuccess: 'Login successful',
    registerSuccess: 'Registration successful',
    invalidCredentials: 'Invalid email or password',
  },
  nav: {
    dashboard: 'Dashboard',
    projects: 'Projects',
    contracts: 'Contracts',
    boq: 'Bill of Quantities',
    claims: 'Claims',
    procurements: 'Procurements',
    financial: 'Financial',
    reports: 'Reports',
    settings: 'Settings',
    users: 'Users',
    audit: 'Audit Log',
    notifications: 'Notifications',
  },
  dashboard: {
    title: 'Dashboard',
    totalProjects: 'Total Projects',
    activeProjects: 'Active Projects',
    totalBudget: 'Total Budget',
    totalEntries: 'Journal Entries',
    recentActivity: 'Recent Activity',
    projectStatus: 'Project Status',
    financialOverview: 'Financial Overview',
  },
  projects: {
    title: 'Projects',
    create: 'Create Project',
    edit: 'Edit Project',
    delete: 'Delete Project',
    code: 'Project Code',
    name: 'Project Name',
    status: 'Status',
    budget: 'Budget',
    client: 'Client',
    location: 'Location',
    planning: 'Planning',
    active: 'Active',
    completed: 'Completed',
    onHold: 'On Hold',
  },
  contracts: {
    title: 'Contracts',
    create: 'Create Contract',
    edit: 'Edit Contract',
    delete: 'Delete Contract',
    number: 'Contract Number',
    projectName: 'Project',
    totalAmount: 'Total Amount',
    status: 'Status',
    draft: 'Draft',
    active: 'Active',
    completed: 'Completed',
  },
  boq: {
    title: 'Bill of Quantities',
    create: 'Create BOQ',
    edit: 'Edit BOQ',
    items: 'Items',
    itemDescription: 'Description',
    quantity: 'Quantity',
    unit: 'Unit',
    unitPrice: 'Unit Price',
    total: 'Total',
    submit: 'Submit',
    approve: 'Approve',
  },
  claims: {
    title: 'Claims',
    create: 'Create Claim',
    claimNumber: 'Claim Number',
    amount: 'Amount',
    status: 'Status',
    pending: 'Pending',
    approved: 'Approved',
    rejected: 'Rejected',
    paid: 'Paid',
  },
  procurement: {
    title: 'Procurements',
    create: 'Create Procurement',
    edit: 'Edit Procurement',
    description: 'Description',
    vendor: 'Vendor',
    amount: 'Amount',
    status: 'Status',
    ordered: 'Ordered',
    received: 'Received',
  },
  financial: {
    title: 'Financial',
    accounts: 'Accounts',
    journalEntries: 'Journal Entries',
    createEntry: 'Create Entry',
    debit: 'Debit',
    credit: 'Credit',
    balance: 'Balance',
    accountType: 'Account Type',
    asset: 'Asset',
    liability: 'Liability',
    equity: 'Equity',
    revenue: 'Revenue',
    expense: 'Expense',
  },
  reports: {
    title: 'Reports',
    financialSummary: 'Financial Summary',
    profitLoss: 'Profit & Loss',
    trialBalance: 'Trial Balance',
    accountBalances: 'Account Balances',
    export: 'Export',
    exportCSV: 'Export as CSV',
    exportExcel: 'Export as Excel',
    exportPDF: 'Export as PDF',
    dateRange: 'Date Range',
    startDate: 'Start Date',
    endDate: 'End Date',
  },
  settings: {
    title: 'Settings',
    general: 'General',
    appearance: 'Appearance',
    language: 'Language',
    notifications: 'Notifications',
    security: 'Security',
  },
  users: {
    title: 'Users',
    manage: 'Manage Users',
    role: 'Role',
    admin: 'Admin',
    manager: 'Manager',
    member: 'Member',
    viewer: 'Viewer',
    addMember: 'Add Member',
    removeMember: 'Remove Member',
    changeRole: 'Change Role',
  },
  common: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    create: 'Create',
    search: 'Search',
    filter: 'Filter',
    export: 'Export',
    import: 'Import',
    loading: 'Loading...',
    noData: 'No data available',
    confirm: 'Confirm',
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Info',
    actions: 'Actions',
    status: 'Status',
    date: 'Date',
    total: 'Total',
    back: 'Back',
    next: 'Next',
    previous: 'Previous',
    page: 'Page',
    of: 'of',
    showMore: 'Show More',
    showLess: 'Show Less',
    all: 'All',
    none: 'None',
    selectAll: 'Select All',
    deselectAll: 'Deselect All',
    required: 'Required',
    optional: 'Optional',
    yes: 'Yes',
    no: 'No',
  },
};

export const ar: TranslationKeys = {
  app: {
    name: '2TO EOS',
    description: 'نظام تخطيط موارد المؤسسات',
  },
  auth: {
    login: 'تسجيل الدخول',
    register: 'تسجيل',
    logout: 'تسجيل الخروج',
    email: 'البريد الإلكتروني',
    password: 'كلمة المرور',
    confirmPassword: 'تأكيد كلمة المرور',
    tenantName: 'اسم المؤسسة',
    forgotPassword: 'نسيت كلمة المرور؟',
    resetPassword: 'إعادة تعيين كلمة المرور',
    loginSuccess: 'تم تسجيل الدخول بنجاح',
    registerSuccess: 'تم التسجيل بنجاح',
    invalidCredentials: 'البريد الإلكتروني أو كلمة المرور غير صحيحة',
  },
  nav: {
    dashboard: 'لوحة التحكم',
    projects: 'المشاريع',
    contracts: 'العقود',
    boq: 'جدول الكميات',
    claims: 'المطالبات',
    procurements: 'المشتريات',
    financial: 'المالية',
    reports: 'التقارير',
    settings: 'الإعدادات',
    users: 'المستخدمين',
    audit: 'سجل المراجعة',
    notifications: 'الإشعارات',
  },
  dashboard: {
    title: 'لوحة التحكم',
    totalProjects: 'إجمالي المشاريع',
    activeProjects: 'المشاريع النشطة',
    totalBudget: 'إجمالي الميزانية',
    totalEntries: 'القيود المحاسبية',
    recentActivity: 'النشاط الأخير',
    projectStatus: 'حالة المشاريع',
    financialOverview: 'نظرة مالية عامة',
  },
  projects: {
    title: 'المشاريع',
    create: 'إنشاء مشروع',
    edit: 'تعديل المشروع',
    delete: 'حذف المشروع',
    code: 'كود المشروع',
    name: 'اسم المشروع',
    status: 'الحالة',
    budget: 'الميزانية',
    client: 'العميل',
    location: 'الموقع',
    planning: 'قيد التخطيط',
    active: 'نشط',
    completed: 'مكتمل',
    onHold: 'معلق',
  },
  contracts: {
    title: 'العقود',
    create: 'إنشاء عقد',
    edit: 'تعديل العقد',
    delete: 'حذف العقد',
    number: 'رقم العقد',
    projectName: 'المشروع',
    totalAmount: 'المبلغ الإجمالي',
    status: 'الحالة',
    draft: 'مسودة',
    active: 'نشط',
    completed: 'مكتمل',
  },
  boq: {
    title: 'جدول الكميات',
    create: 'إنشاء جدول',
    edit: 'تعديل الجدول',
    items: 'الأصناف',
    itemDescription: 'الوصف',
    quantity: 'الكمية',
    unit: 'الوحدة',
    unitPrice: 'سعر الوحدة',
    total: 'الإجمالي',
    submit: 'إرسال',
    approve: 'اعتماد',
  },
  claims: {
    title: 'المطالبات',
    create: 'إنشاء مطالبة',
    claimNumber: 'رقم المطالبة',
    amount: 'المبلغ',
    status: 'الحالة',
    pending: 'قيد المراجعة',
    approved: 'معتمدة',
    rejected: 'مرفوضة',
    paid: 'مدفوعة',
  },
  procurement: {
    title: 'المشتريات',
    create: 'إنشاء مشتريات',
    edit: 'تعديل المشتريات',
    description: 'الوصف',
    vendor: 'المورد',
    amount: 'المبلغ',
    status: 'الحالة',
    ordered: 'تم الطلب',
    received: 'تم الاستلام',
  },
  financial: {
    title: 'المالية',
    accounts: 'الحسابات',
    journalEntries: 'القيود اليومية',
    createEntry: 'إنشاء قيد',
    debit: 'مدين',
    credit: 'دائن',
    balance: 'الرصيد',
    accountType: 'نوع الحساب',
    asset: 'أصول',
    liability: 'خصوم',
    equity: 'حقوق ملكية',
    revenue: 'إيرادات',
    expense: 'مصروفات',
  },
  reports: {
    title: 'التقارير',
    financialSummary: 'ملخص مالي',
    profitLoss: 'الأرباح والخسائر',
    trialBalance: 'ميزان المراجعة',
    accountBalances: 'أرصدة الحسابات',
    export: 'تصدير',
    exportCSV: 'تصدير كـ CSV',
    exportExcel: 'تصدير كـ Excel',
    exportPDF: 'تصدير كـ PDF',
    dateRange: 'نطاق التاريخ',
    startDate: 'تاريخ البداية',
    endDate: 'تاريخ النهاية',
  },
  settings: {
    title: 'الإعدادات',
    general: 'عام',
    appearance: 'المظهر',
    language: 'اللغة',
    notifications: 'الإشعارات',
    security: 'الأمان',
  },
  users: {
    title: 'المستخدمين',
    manage: 'إدارة المستخدمين',
    role: 'الدور',
    admin: 'مدير',
    manager: 'مشرف',
    member: 'عضو',
    viewer: 'مشاهد',
    addMember: 'إضافة عضو',
    removeMember: 'إزالة عضو',
    changeRole: 'تغيير الدور',
  },
  common: {
    save: 'حفظ',
    cancel: 'إلغاء',
    delete: 'حذف',
    edit: 'تعديل',
    create: 'إنشاء',
    search: 'بحث',
    filter: 'تصفية',
    export: 'تصدير',
    import: 'استيراد',
    loading: 'جاري التحميل...',
    noData: 'لا توجد بيانات',
    confirm: 'تأكيد',
    success: 'نجاح',
    error: 'خطأ',
    warning: 'تحذير',
    info: 'معلومات',
    actions: 'إجراءات',
    status: 'الحالة',
    date: 'التاريخ',
    total: 'الإجمالي',
    back: 'رجوع',
    next: 'التالي',
    previous: 'السابق',
    page: 'صفحة',
    of: 'من',
    showMore: 'عرض المزيد',
    showLess: 'عرض أقل',
    all: 'الكل',
    none: 'لا شيء',
    selectAll: 'تحديد الكل',
    deselectAll: 'إلغاء التحديد',
    required: 'مطلوب',
    optional: 'اختياري',
    yes: 'نعم',
    no: 'لا',
  },
};
