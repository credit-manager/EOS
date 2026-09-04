import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Translation resources
const resources = {
  en: {
    translation: {
      // Common
      'welcome': 'Welcome to EOS ERP Platform',
      'login': 'Login',
      'logout': 'Logout',
      'dashboard': 'Dashboard',
      'loading': 'Loading...',
      'save': 'Save',
      'cancel': 'Cancel',
      'delete': 'Delete',
      'edit': 'Edit',
      'create': 'Create',
      'search': 'Search',
      'filter': 'Filter',
      'export': 'Export',
      'import': 'Import',
      
      // Navigation
      'home': 'Home',
      'industries': 'Industries',
      'builder': 'ERP Builder',
      'entities': 'Entities',
      'reports': 'Reports',
      'settings': 'Settings',
      
      // Industries
      'select_industry': 'Select Your Industry',
      'construction': 'Construction & Contracting',
      'tourism': 'Tourism & Travel',
      'trading': 'Trading & Distribution',
      'manufacturing': 'Manufacturing',
      'retail': 'Retail & POS',
      'services': 'Professional Services',
      'restaurant': 'Restaurants & Food',
      'healthcare': 'Healthcare',
      'education': 'Education',
      'real_estate': 'Real Estate',
      
      // Builder
      'build_erp': 'Build Your ERP',
      'business_description': 'Business Description',
      'describe_business': 'Describe your business in natural language...',
      'ai_compose': 'AI Compose',
      'generating': 'Generating your ERP configuration...',
      'modules_selected': 'Modules Selected',
      'entities_created': 'Entities Created',
      'workflows_configured': 'Workflows Configured',
      'preview': 'Preview',
      'publish': 'Publish',
      'draft': 'Draft',
      'published': 'Published',
      
      // Entities
      'entity_name': 'Entity Name',
      'fields': 'Fields',
      'relationships': 'Relationships',
      'add_field': 'Add Field',
      'field_type': 'Field Type',
      'required': 'Required',
      'unique': 'Unique',
      'validation_rules': 'Validation Rules',
      
      // Reports
      'financial_reports': 'Financial Reports',
      'operational_reports': 'Operational Reports',
      'custom_reports': 'Custom Reports',
      'trial_balance': 'Trial Balance',
      'profit_loss': 'Profit & Loss',
      'balance_sheet': 'Balance Sheet',
      'cash_flow': 'Cash Flow',
      
      // Auth
      'email': 'Email',
      'password': 'Password',
      'remember_me': 'Remember Me',
      'forgot_password': 'Forgot Password?',
      'sign_in': 'Sign In',
      'invalid_credentials': 'Invalid email or password',
      
      // Settings
      'profile': 'Profile',
      'company_settings': 'Company Settings',
      'users_roles': 'Users & Roles',
      'integrations': 'Integrations',
      'language': 'Language',
      'theme': 'Theme',
      'notifications': 'Notifications',
    }
  },
  ar: {
    translation: {
      // Common
      'welcome': 'مرحباً بك في منصة EOS لإدارة الموارد',
      'login': 'تسجيل الدخول',
      'logout': 'تسجيل الخروج',
      'dashboard': 'لوحة التحكم',
      'loading': 'جاري التحميل...',
      'save': 'حفظ',
      'cancel': 'إلغاء',
      'delete': 'حذف',
      'edit': 'تعديل',
      'create': 'إنشاء',
      'search': 'بحث',
      'filter': 'تصفية',
      'export': 'تصدير',
      'import': 'استيراد',
      
      // Navigation
      'home': 'الرئيسية',
      'industries': 'القطاعات',
      'builder': 'منشئ النظام',
      'entities': 'الكيانات',
      'reports': 'التقارير',
      'settings': 'الإعدادات',
      
      // Industries
      'select_industry': 'اختر قطاع عملك',
      'construction': 'المقاولات والبناء',
      'tourism': 'السياحة والسفر',
      'trading': 'التجارة والتوزيع',
      'manufacturing': 'التصنيع',
      'retail': 'التجزئة ونقاط البيع',
      'services': 'الخدمات المهنية',
      'restaurant': 'المطاعم والأغذية',
      'healthcare': 'الرعاية الصحية',
      'education': 'التعليم',
      'real_estate': 'العقارات',
      
      // Builder
      'build_erp': 'ابنِ نظام ERP الخاص بك',
      'business_description': 'وصف النشاط التجاري',
      'describe_business': 'صِف نشاطك التجاري باللغة الطبيعية...',
      'ai_compose': 'توليد بالذكاء الاصطناعي',
      'generating': 'جاري توليد إعدادات النظام...',
      'modules_selected': 'الوحدات المختارة',
      'entities_created': 'الكيانات المُنشأة',
      'workflows_configured': 'سير العمل المُعدّة',
      'preview': 'معاينة',
      'publish': 'نشر',
      'draft': 'مسودة',
      'published': 'منشور',
      
      // Entities
      'entity_name': 'اسم الكيان',
      'fields': 'الحقول',
      'relationships': 'العلاقات',
      'add_field': 'إضافة حقل',
      'field_type': 'نوع الحقل',
      'required': 'مطلوب',
      'unique': 'فريد',
      'validation_rules': 'قواعد التحقق',
      
      // Reports
      'financial_reports': 'التقارير المالية',
      'operational_reports': 'التقارير التشغيلية',
      'custom_reports': 'تقارير مخصصة',
      'trial_balance': 'ميزان المراجعة',
      'profit_loss': 'قائمة الأرباح والخسائر',
      'balance_sheet': 'الميزانية العمومية',
      'cash_flow': 'قائمة التدفقات النقدية',
      
      // Auth
      'email': 'البريد الإلكتروني',
      'password': 'كلمة المرور',
      'remember_me': 'تذكرني',
      'forgot_password': 'نسيت كلمة المرور؟',
      'sign_in': 'تسجيل الدخول',
      'invalid_credentials': 'البريد الإلكتروني أو كلمة المرور غير صحيحة',
      
      // Settings
      'profile': 'الملف الشخصي',
      'company_settings': 'إعدادات الشركة',
      'users_roles': 'المستخدمين والصلاحيات',
      'integrations': 'التكاملات',
      'language': 'اللغة',
      'theme': 'السمة',
      'notifications': 'الإشعارات',
    }
  }
}

export function initI18n() {
  i18n.use(initReactI18next).init({
    resources,
    lng: 'ar', // Default language is Arabic
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false,
    },
  })
}

export default i18n
