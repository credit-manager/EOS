"""
🔒 مراجعة أمنية شاملة - Multi-Tenancy & Security
تاريخ المراجعة: 2024
النطاق: عزل المستأجرين، Rate Limiting، 2FA، Secrets Management
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class SecurityAudit:
    """مراجعة أمنية شاملة للمنصة"""
    
    def __init__(self):
        self.findings = []
        self.critical = []
        self.high = []
        self.medium = []
        self.low = []
        
    def audit_multi_tenancy(self) -> List[Dict]:
        """مراجعة عزل المستأجرين"""
        findings = []
        
        # فحص models.py
        try:
            with open('models.py', 'r') as f:
                content = f.read()
                
            # البحث عن tenant_id nullable
            if 'tenant_id.*nullable=True' in content or 'Column.*tenant_id.*nullable=True' in content:
                finding = {
                    'id': 'SEC-001',
                    'severity': 'CRITICAL',
                    'category': 'Multi-Tenancy',
                    'title': 'tenant_id قابل للقيمة NULL',
                    'description': 'وجود tenant_id كـ nullable يسمح بوجود بيانات بدون مستأجر، مما قد يسبب تسرب بيانات',
                    'location': 'models.py - DBPEntity.tenant_id',
                    'recommendation': 'تغيير nullable=False وإضافة default value أو validation',
                    'code_example': 'tenant_id = Column(String(36), nullable=False, index=True)'
                }
                findings.append(finding)
                self.critical.append(finding)
            
            # فحص dynamic_crud.py
            try:
                with open('routers/dynamic_crud.py', 'r') as f:
                    crud_content = f.read()
                    
                # التحقق من فرض tenant_id
                if 'tenant_id' in crud_content and 'authenticate' in crud_content:
                    finding = {
                        'id': 'SEC-002',
                        'severity': 'INFO',
                        'category': 'Multi-Tenancy',
                        'title': 'فرض tenant_id من المستخدم المصادق',
                        'description': 'يتم استخراج tenant_id من المستخدم المصادق عليه بدلاً من الطلب',
                        'location': 'routers/dynamic_crud.py',
                        'recommendation': 'استمرار تطبيق هذا النمط على جميع endpoints',
                        'status': 'Implemented'
                    }
                    findings.append(finding)
                    self.low.append(finding)
                    
            except FileNotFoundError:
                pass
                
        except FileNotFoundError:
            pass
            
        return findings
    
    def audit_rate_limiting(self) -> List[Dict]:
        """مراجعة Rate Limiting"""
        findings = []
        
        try:
            with open('core/rate_limit.py', 'r') as f:
                content = f.read()
                
            # التحقق من الميزات
            has_db_backed = 'Session' in content or 'database' in content.lower()
            has_sliding_window = 'sliding' in content.lower() or 'window' in content.lower()
            has_per_endpoint = 'endpoint' in content.lower()
            
            if has_db_backed and has_sliding_window:
                finding = {
                    'id': 'SEC-003',
                    'severity': 'INFO',
                    'category': 'Rate Limiting',
                    'title': 'نظام Rate Limiting متقدم',
                    'description': 'يوجد نظام rate limiting بـ DB-backed و Sliding window',
                    'location': 'core/rate_limit.py',
                    'recommendation': 'التأكد من تطبيقه على جميع endpoints الحساسة',
                    'features': {
                        'db_backed': has_db_backed,
                        'sliding_window': has_sliding_window,
                        'per_endpoint': has_per_endpoint
                    }
                }
                findings.append(finding)
                self.low.append(finding)
            else:
                finding = {
                    'id': 'SEC-004',
                    'severity': 'MEDIUM',
                    'category': 'Rate Limiting',
                    'title': 'Rate Limiting غير مكتمل',
                    'description': 'نظام rate limit موجود لكن يحتاج التأكد من شموليته',
                    'location': 'core/rate_limit.py',
                    'recommendation': 'تطبيق rate limiting على جميع endpoints الحساسة'
                }
                findings.append(finding)
                self.medium.append(finding)
                
        except FileNotFoundError:
            finding = {
                'id': 'SEC-005',
                'severity': 'HIGH',
                'category': 'Rate Limiting',
                'title': 'لا يوجد Rate Limiting',
                'description': 'لم يتم العثور على ملف rate_limit.py',
                'recommendation': 'إنشاء نظام rate limiting فوراً'
            }
            findings.append(finding)
            self.high.append(finding)
            
        return findings
    
    def audit_2fa(self) -> List[Dict]:
        """مراجعة 2FA implementation"""
        findings = []
        
        try:
            with open('core/two_factor.py', 'r') as f:
                content = f.read()
                
            # التحقق من التشفير
            has_encryption = 'encrypt' in content.lower() or 'cipher' in content.lower() or 'Fernet' in content
            has_totp = 'totp' in content.lower() or 'TOTP' in content
            has_recovery = 'recovery' in content.lower()
            
            if not has_encryption:
                finding = {
                    'id': 'SEC-006',
                    'severity': 'CRITICAL',
                    'category': '2FA',
                    'title': '2FA Secrets غير مشفرة',
                    'description': 'يتم تخزين أسرار 2FA كنص صريح في قاعدة البيانات',
                    'location': 'core/two_factor.py',
                    'recommendation': 'تشفير secrets باستخدام Fernet أو AES قبل التخزين',
                    'code_example': '''from cryptography.fernet import Fernet\nf = Fernet(secret_key)\nencrypted = f.encrypt(secret.encode())'''
                }
                findings.append(finding)
                self.critical.append(finding)
            else:
                finding = {
                    'id': 'SEC-007',
                    'severity': 'INFO',
                    'category': '2FA',
                    'title': '2FA Secrets مشفرة',
                    'description': 'يتم تشفير أسرار 2FA بشكل صحيح',
                    'location': 'core/two_factor.py',
                    'status': 'Implemented'
                }
                findings.append(finding)
                self.low.append(finding)
                
            if has_totp:
                finding = {
                    'id': 'SEC-008',
                    'severity': 'INFO',
                    'category': '2FA',
                    'title': 'TOTP مدعوم',
                    'description': 'دعم TOTP لـ 2FA',
                    'location': 'core/two_factor.py'
                }
                findings.append(finding)
                self.low.append(finding)
                
        except FileNotFoundError:
            finding = {
                'id': 'SEC-009',
                'severity': 'HIGH',
                'category': '2FA',
                'title': 'لا يوجد تطبيق 2FA',
                'description': 'لم يتم العثور على ملف two_factor.py',
                'recommendation': 'تنفيذ 2FA باستخدام TOTP'
            }
            findings.append(finding)
            self.high.append(finding)
            
        return findings
    
    def audit_secrets_management(self) -> List[Dict]:
        """مراجعة إدارة الأسرار"""
        findings = []
        
        # التحقق من استخدام .env
        env_exists = os.path.exists('.env.example')
        
        # البحث عن hardcoded secrets
        hardcoded_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
        ]
        
        for root, dirs, files in os.walk('.'):
            if '.git' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                            for pattern in hardcoded_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                if matches:
                                    # استبعاد الأمثلة والتوثيق
                                    if 'example' not in filepath.lower() and 'test' not in filepath.lower():
                                        finding = {
                                            'id': f'SEC-010-{len(findings)}',
                                            'severity': 'HIGH',
                                            'category': 'Secrets Management',
                                            'title': 'Hardcoded Secret محتمل',
                                            'description': f'تم العثور على نمط يطابق secret في {filepath}',
                                            'location': filepath,
                                            'recommendation': 'نقل السر إلى متغير بيئة واستخدام os.environ'
                                        }
                                        findings.append(finding)
                                        self.high.append(finding)
                    except:
                        pass
        
        if env_exists:
            finding = {
                'id': 'SEC-011',
                'severity': 'INFO',
                'category': 'Secrets Management',
                'title': '.env.example موجود',
                'description': 'يوجد ملف توثيق للمتغيرات البيئية',
                'location': '.env.example',
                'recommendation': 'استخدام Vault أو AWS Secrets Manager في الإنتاج'
            }
            findings.append(finding)
            self.low.append(finding)
        else:
            finding = {
                'id': 'SEC-012',
                'severity': 'MEDIUM',
                'category': 'Secrets Management',
                'title': 'لا يوجد .env.example',
                'description': 'لم يتم العثور على ملف توثيق المتغيرات',
                'recommendation': 'إنشاء .env.example موثق'
            }
            findings.append(finding)
            self.medium.append(finding)
            
        return findings
    
    def generate_report(self) -> str:
        """إنشاء التقرير الأمني"""
        report = []
        report.append("# 🔒 تقرير المراجعة الأمنية الشاملة")
        report.append("**تاريخ المراجعة**: 2024")
        report.append("**النطاق**: Multi-Tenancy, Rate Limiting, 2FA, Secrets Management")
        report.append("")
        
        # ملخص
        report.append("## 📊 الملخص التنفيذي")
        report.append(f"- 🔴 Critical: {len(self.critical)}")
        report.append(f"- 🟠 High: {len(self.high)}")
        report.append(f"- 🟡 Medium: {len(self.medium)}")
        report.append(f"- 🟢 Low/Info: {len(self.low)}")
        report.append(f"- **الإجمالي**: {len(self.critical) + len(self.high) + len(self.medium) + len(self.low)}")
        report.append("")
        
        # Critical Findings
        if self.critical:
            report.append("## 🔴 Critical Findings (Immediate Action Required)")
            for finding in self.critical:
                report.append(f"### {finding['id']}: {finding['title']}")
                report.append(f"**الموقع**: {finding.get('location', 'N/A')}")
                report.append(f"**الوصف**: {finding['description']}")
                report.append(f"**التوصية**: {finding['recommendation']}")
                if 'code_example' in finding:
                    report.append(f"```python\n{finding['code_example']}\n```")
                report.append("")
        
        # High Findings
        if self.high:
            report.append("## 🟠 High Priority Findings")
            for finding in self.high:
                report.append(f"### {finding['id']}: {finding['title']}")
                report.append(f"**الموقع**: {finding.get('location', 'N/A')}")
                report.append(f"**الوصف**: {finding['description']}")
                report.append(f"**التوصية**: {finding['recommendation']}")
                report.append("")
        
        # Medium Findings
        if self.medium:
            report.append("## 🟡 Medium Priority Findings")
            for finding in self.medium:
                report.append(f"### {finding['id']}: {finding['title']}")
                report.append(f"**الموقع**: {finding.get('location', 'N/A')}")
                report.append(f"**الوصف**: {finding['description']}")
                report.append(f"**التوصية**: {finding['recommendation']}")
                report.append("")
        
        # Low/Info Findings
        if self.low:
            report.append("## 🟢 Low/Info Findings")
            for finding in self.low:
                report.append(f"### {finding['id']}: {finding['title']}")
                report.append(f"**الوصف**: {finding['description']}")
                if finding.get('status') == 'Implemented':
                    report.append("**الحالة**: ✅ Implemented")
                report.append("")
        
        # خطة العمل
        report.append("## 🎯 خطة العمل المقترحة")
        report.append("### المرحلة 1 (فورية - 24 ساعة):")
        report.append("- معالجة جميع Critical findings")
        report.append("- إصلاح tenant_id nullable")
        report.append("- تشفير 2FA secrets")
        report.append("")
        report.append("### المرحلة 2 (أسبوع):")
        report.append("- معالجة High priority findings")
        report.append("- تطبيق rate limiting شامل")
        report.append("- مراجعة secrets management")
        report.append("")
        report.append("### المرحلة 3 (شهر):")
        report.append("- معالجة Medium findings")
        report.append("- اختبارات اختراق شاملة")
        report.append("- توثيق أمني كامل")
        report.append("")
        
        return '\n'.join(report)


if __name__ == "__main__":
    audit = SecurityAudit()
    audit.audit_multi_tenancy()
    audit.audit_rate_limiting()
    audit.audit_2fa()
    audit.audit_secrets_management()
    print(audit.generate_report())
