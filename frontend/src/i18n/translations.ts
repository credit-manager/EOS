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
    home: string;
    businessObjects: string;
    businessGraph: string;
    workflows: string;
    rules: string;
    events: string;
    analytics: string;
    aiCopilot: string;
    documents: string;
    integrations: string;
    globalization: string;
    builder: string;
    developerSdk: string;
    marketplace: string;
    workspace: string;
    overview: string;
    tenants: string;
    rolesPermissions: string;
    plans: string;
    billing: string;
    featureFlags: string;
    aiControlCenter: string;
    automation: string;
    applications: string;
    apiManagement: string;
    securityCenter: string;
    auditLogs: string;
    systemHealth: string;
    backupRecovery: string;
    support: string;
    search: string;
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
    systemHealth: string;
    allSystems: string;
    revenueGrowth: string;
    tenantGrowth: string;
    userGrowth: string;
    aiUsage: string;
    operational: string;
    warning: string;
    critical: string;
    newTenantRegistered: string;
    paymentProcessed: string;
    aiModelUpdated: string;
    userSuspended: string;
    backupCompleted: string;
    minutesAgo: string;
    hoursAgo: string;
    daysAgo: string;
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
    titleField: string;
    counterparty: string;
    totalAmount: string;
    status: string;
    draft: string;
    pendingApproval: string;
    active: string;
    completed: string;
    terminated: string;
    signedDate: string;
    completionDate: string;
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
    date: string;
    period: string;
    pending: string;
    draft: string;
    submitted: string;
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
    requisitionNumber: string;
    project: string;
    priority: string;
    low: string;
    medium: string;
    high: string;
    urgent: string;
    draft: string;
    pendingApproval: string;
    approved: string;
    ordered: string;
    received: string;
    invoiced: string;
    paid: string;
    cancelled: string;
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
    skip: string;
  };
  landing: {
    features: string;
    pricing: string;
    docs: string;
    signIn: string;
    heroTitle1: string;
    heroTitle2: string;
    heroSubtitle: string;
    startTrial: string;
    watchDemo: string;
    problemTitle: string;
    solutionTitle: string;
    solutionSubtitle: string;
    ctaTitle: string;
    ctaSubtitle: string;
    getStarted: string;
    learnMore: string;
    tools: string[];
    footerRights: string;
  };
  login: {
    backToHome: string;
    title: string;
    subtitle: string;
    emailLabel: string;
    passwordLabel: string;
    signIn: string;
    signingIn: string;
    noAccount: string;
    createWorkspace: string;
  };
  onboard: {
    welcomeTitle: string;
    welcomeSubtitle: string;
    getStarted: string;
    companyName: string;
    companyNamePlaceholder: string;
    industry: string;
    industryPlaceholder: string;
    inviteTeam: string;
    invitePlaceholder: string;
    completeTitle: string;
    completeSubtitle: string;
    goToDashboard: string;
  };
  sidebar: {
    platform: string;
    erp: string;
    administration: string;
    master: string;
  };
  adminSidebar: {
    eosControlCenter: string;
    systemOwner: string;
    superAdmin: string;
    featureFlags: string;
    securityCenter: string;
    auditLogs: string;
    systemHealth: string;
    systemSettings: string;
    globalSearch: string;
    notificationsCenter: string;
    backupRecovery: string;
    apiManagement: string;
    automationCenter: string;
    supportCenter: string;
    applications: string;
    integrationsHub: string;
    master: string;
    overview: string;
    groupOrganization: string;
    groupCommerce: string;
    groupPlatform: string;
    groupAi: string;
    groupAutomation: string;
    groupSecurity: string;
    groupSystem: string;
    groupSupport: string;
    groupMaster: string;
    tenants: string;
    users: string;
    rolesPermissions: string;
    plans: string;
    subscriptions: string;
    billing: string;
    transactions: string;
    aiControlCenter: string;
    aiModels: string;
    aiWorkforce: string;
    aiUsage: string;
    workflows: string;
    automations: string;
    jobs: string;
    sessions: string;
    monitoring: string;
    tickets: string;
    supportPage: string;
  };
  adminHeader: {
    quickActions: string;
    newTenant: string;
    newUser: string;
    newPlan: string;
    newRole: string;
    newApiKey: string;
    newAiAgent: string;
    disableSystem: string;
    notifications: string;
    searchPlaceholder: string;
    confirmDangerousAction: string;
    confirmDangerousMessage: string;
  };
  master: {
    title: string;
    subtitle: string;
    overview: {
      title: string;
      totalTenants: string;
      activeTenants: string;
      suspendedTenants: string;
      totalUsers: string;
      activeUsers: string;
      newTenants: string;
      mrr: string;
      arr: string;
      revenue: string;
      outstandingPayments: string;
      aiUsage: string;
      apiUsage: string;
      automationRuns: string;
      storageUsage: string;
      analyticsTab: string;
    };
    health: {
      title: string;
      apiStatus: string;
      databaseStatus: string;
      aiServicesStatus: string;
      backgroundJobs: string;
      queueStatus: string;
      storageStatus: string;
      emailService: string;
      paymentGateway: string;
      externalIntegrations: string;
      aiServices: string;
      storage: string;
      integrations: string;
      cpu: string;
      ram: string;
      disk: string;
      database: string;
      apiLatency: string;
      requestsPerSec: string;
      errorRate: string;
      queue: string;
      operational: string;
      warning: string;
      critical: string;
      offline: string;
    };
    tenants: {
      title: string;
      searchPlaceholder: string;
      companyName: string;
      owner: string;
      industry: string;
      country: string;
      plan: string;
      status: string;
      users: string;
      storage: string;
      aiUsage: string;
      createdAt: string;
      lastActivity: string;
      actions: string;
      view: string;
      edit: string;
      suspend: string;
      activate: string;
      delete: string;
      impersonate: string;
      changePlan: string;
    };
    users: {
      title: string;
      searchPlaceholder: string;
      user: string;
      email: string;
      tenant: string;
      role: string;
      status: string;
      mfa: string;
      lastLogin: string;
      created: string;
      sessions: string;
      riskStatus: string;
      actions: string;
      view: string;
      edit: string;
      suspend: string;
      activate: string;
      resetPassword: string;
      forceLogout: string;
      resetMFA: string;
      delete: string;
    };
    roles: {
      title: string;
      systemRoles: string;
      tenantRoles: string;
      customRoles: string;
      permissions: string;
      permissionGroups: string;
    };
    plans: {
      title: string;
      pricing: string;
      features: string;
      limits: string;
      trialPeriod: string;
      usageLimits: string;
      aiLimits: string;
      storageLimits: string;
      userLimits: string;
      apiLimits: string;
      actions: {
        createPlan: string;
        editPlan: string;
        duplicatePlan: string;
        archivePlan: string;
        changePricing: string;
        configureFeatures: string;
      };
    };
    billing: {
      title: string;
      revenue: string;
      mrr: string;
      arr: string;
      invoices: string;
      payments: string;
      failedPayments: string;
      refunds: string;
      taxes: string;
      transactions: string;
    };
    featureFlags: {
      title: string;
      erp: string;
      aiWorkforce: string;
      automation: string;
      analytics: string;
      industryOS: string;
      advancedReports: string;
      api: string;
      integrations: string;
      global: string;
      byPlan: string;
      byTenant: string;
      byUser: string;
      enable: string;
      disable: string;
      rolloutPercent: string;
    };
    aiControl: {
      title: string;
      models: string;
      providers: string;
      modelUsage: string;
      tokenUsage: string;
      cost: string;
      requests: string;
      latency: string;
      errors: string;
      aiAgents: string;
      aiWorkforce: string;
      promptManagement: string;
      aiPolicies: string;
      modelRouting: string;
      modelManagement: {
        provider: string;
        modelName: string;
        status: string;
        cost: string;
        contextWindow: string;
        rateLimits: string;
        default: string;
        backup: string;
        enable: string;
        disable: string;
        configure: string;
        setDefault: string;
        setFallback: string;
      };
    };
    automation: {
      title: string;
      workflows: string;
      automations: string;
      jobs: string;
      automationName: string;
      tenant: string;
      trigger: string;
      status: string;
      executions: string;
      successRate: string;
      errors: string;
      lastRun: string;
      actions: {
        enable: string;
        disable: string;
        edit: string;
        duplicate: string;
        test: string;
        viewLogs: string;
      };
    };
    integrations: {
      title: string;
      payment: string;
      email: string;
      sms: string;
      whatsapp: string;
      accounting: string;
      crm: string;
      storage: string;
      aiProviders: string;
      webhooks: string;
      apis: string;
      integration: string;
      provider: string;
      connectedTenants: string;
      errors: string;
      lastSync: string;
    };
    api: {
      title: string;
      apiKeys: string;
      apiClients: string;
      requests: string;
      rateLimits: string;
      webhooks: string;
      apiErrors: string;
      apiUsage: string;
      createApiKey: string;
      revoke: string;
      rotate: string;
      setPermissions: string;
      setRateLimits: string;
    };
    security: {
      title: string;
      loginAttempts: string;
      failedLogins: string;
      suspiciousActivity: string;
      activeSessions: string;
      mfaStatus: string;
      securityEvents: string;
      ipActivity: string;
      apiSecurity: string;
      accessViolations: string;
      forceLogout: string;
      blockIP: string;
      revokeToken: string;
      disableAccount: string;
      requireMFA: string;
    };
    auditLogs: {
      title: string;
      user: string;
      tenant: string;
      action: string;
      resource: string;
      timestamp: string;
      ip: string;
      device: string;
      result: string;
      filters: {
        date: string;
        user: string;
        tenant: string;
        action: string;
        resource: string;
        ip: string;
        success: string;
        failure: string;
      };
    };
    systemHealth: {
      title: string;
      cpu: string;
      ram: string;
      disk: string;
      database: string;
      apiLatency: string;
      requestsPerSec: string;
      errorRate: string;
      queue: string;
      backgroundJobs: string;
      activeIncidents: string;
      warnings: string;
      resolvedIncidents: string;
    };
    backups: {
      title: string;
      databaseBackups: string;
      fileBackups: string;
      backupSchedule: string;
      backupStatus: string;
      restorePoints: string;
      createBackup: string;
      restore: string;
      download: string;
      delete: string;
      configureSchedule: string;
    };
    notifications: {
      title: string;
      global: string;
      tenantSpecific: string;
      userSpecific: string;
      announcement: string;
      maintenance: string;
      security: string;
      billing: string;
      systemAlert: string;
    };
    support: {
      title: string;
      supportTickets: string;
      tenantIssues: string;
      userIssues: string;
      systemIssues: string;
      ticket: string;
      priority: string;
      status: string;
      assignedTo: string;
      created: string;
      updated: string;
    };
    quickActions: {
      create: string;
      newTenant: string;
      newUser: string;
      newPlan: string;
      newRole: string;
      newFeature: string;
      newNotification: string;
      newApiKey: string;
      newAiAgent: string;
    };
    settings: {
      general: string;
      email: string;
      notifications: string;
      security: string;
      system: string;
      ai: string;
    };
    common: {
      loading: string;
      search: string;
      noData: string;
      total: string;
      actions: string;
      view: string;
      edit: string;
      delete: string;
      suspend: string;
      activate: string;
      enable: string;
      disable: string;
      confirm: string;
      cancel: string;
      save: string;
      close: string;
      create: string;
      new: string;
      filter: string;
      all: string;
      success: string;
      failed: string;
      warning: string;
      active: string;
      inactive: string;
      back: string;
      next: string;
      export: string;
      import: string;
      download: string;
      upload: string;
      refresh: string;
      retry: string;
      createdAt: string;
      updatedAt: string;
      lastActive: string;
    };
  };
  applications: {
    title: string;
    subtitle: string;
    tenants: string;
  };
  globalSearch: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
  };
  integrationsHub: {
    title: string;
    subtitle: string;
    lastSync: string;
    configure: string;
    realtime: string;
    tenants: string;
  };
  systemHealth: {
    title: string;
    subtitle: string;
    systemIncidents: string;
    backgroundJobs: string;
    elevatedDisk: string;
    queueBacklog: string;
    scheduledMaintenance: string;
    dailyBackup: string;
    aiModelTraining: string;
    emailDispatch: string;
    reportGeneration: string;
  };
  systemSettings: {
    title: string;
    subtitle: string;
    saveChanges: string;
    generalTab: string;
    emailTab: string;
    notificationsTab: string;
    securityTab: string;
    systemTab: string;
    aiTab: string;
    platformName: string;
    defaultLanguage: string;
    timezone: string;
    defaultCurrency: string;
    smtpHost: string;
    senderEmail: string;
    templates: string;
    emailNotifications: string;
    pushNotifications: string;
    smsAlerts: string;
    sessionTimeout: string;
    passwordMinLength: string;
    mfaRequired: string;
    maintenanceMode: string;
    debugMode: string;
    cacheDuration: string;
    defaultModel: string;
    fallbackModel: string;
    tokenLimit: string;
  };
  securityCenter: {
    title: string;
    subtitle: string;
    recentEvents: string;
    type: string;
    user: string;
    ip: string;
    result: string;
    time: string;
    device: string;
  };
  notificationsCenter: {
    title: string;
    subtitle: string;
    sendNotification: string;
    notificationTitle: string;
    message: string;
    scope: string;
    category: string;
    send: string;
  };
  backupRecovery: {
    title: string;
    subtitle: string;
    lastBackup: string;
    totalBackups: string;
    createBackup: string;
    restore: string;
    id: string;
    type: string;
    size: string;
    status: string;
    date: string;
    duration: string;
  };
  apiManagement: {
    title: string;
    subtitle: string;
    totalRequests: string;
    activeKeys: string;
    createApiKey: string;
    key: string;
    name: string;
    tenant: string;
    requests: string;
    rateLimit: string;
    rotate: string;
    revoke: string;
  };
  automationCenter: {
    title: string;
    subtitle: string;
    newAutomation: string;
    name: string;
    tenant: string;
    trigger: string;
    executions: string;
    successRate: string;
    lastRun: string;
    running: string;
    paused: string;
    failed: string;
  };
  supportCenter: {
    title: string;
    subtitle: string;
    newTicket: string;
    ticket: string;
    tenant: string;
    priority: string;
    assigned: string;
    created: string;
    open: string;
    inProgress: string;
    resolved: string;
  };
  executiveDashboard: {
    searchPlaceholder: string;
    workspace: string;
    whatNeedsAttention: string;
    askEos: string;
    askEosSubtitle: string;
    askEosPlaceholder: string;
    analyzing: string;
    analysisComplete: string;
    aiFallbackResponse: string;
    suggestApproval: string;
    suggestOverdue: string;
    suggestArAging: string;
    suggestProjectHealth: string;
    suggestTopSuppliers: string;
    suggestBudgetReport: string;
    statRecords: string;
    statApprovals: string;
    statWorkflows: string;
    statArOutstanding: string;
    statApOutstanding: string;
    statDocuments: string;
    tabOverview: string;
    tabAttention: string;
    tabFinancial: string;
    tabRisks: string;
    tabActivity: string;
    quickNavigation: string;
    businessObjects: string;
    noDataYet: string;
    recentEvents: string;
    noEventsYet: string;
    pendingApprovals: string;
    approve: string;
    reject: string;
    allClearNoApprovals: string;
    overdueInvoices: string;
    due: string;
    noOverdueInvoices: string;
    overdueBills: string;
    noOverdueBills: string;
    activeWorkflows: string;
    state: string;
    noActiveWorkflows: string;
    arAging: string;
    apAging: string;
    current: string;
    totalAr: string;
    totalAp: string;
    noData: string;
    recentInvoices: string;
    noInvoices: string;
    dueAmount: string;
    recentBills: string;
    noBills: string;
    noDetectedRisks: string;
    allSystemsNormal: string;
    ruleActivity: string;
    noRuleFirings: string;
    documentIntelligence: string;
    docTotal: string;
    docProcessed: string;
    docProcessing: string;
    docFailed: string;
    activeProjects: string;
    noClient: string;
    budgetSuffix: string;
    actionLabel: string;
  };
  businessObjectsExplorer: {
    title: string;
    publishedEntities: string;
    searchPlaceholder: string;
    fields: string;
    noObjectsFound: string;
    publishHint: string;
  };
  businessGraph: {
    title: string;
    subtitle: string;
    entityType: string;
    record: string;
    depth: string;
    loading: string;
    noRecords: string;
    refreshGraph: string;
    nodes: string;
    edges: string;
    entityTypes: string;
    entryNode: string;
    entity: string;
    titleLabel: string;
    recordId: string;
    selectToVisualize: string;
    nodeDetails: string;
    connections: string;
    data: string;
    entityLegend: string;
  };
  workflowsPage: {
    title: string;
    subtitle: string;
    tabInstances: string;
    tabApprovals: string;
    tabTemplates: string;
    tabHistory: string;
    startWorkflow: string;
    refresh: string;
    noInstances: string;
    noInstancesHint: string;
    startNewWorkflow: string;
    template: string;
    selectTemplate: string;
    referenceType: string;
    referenceTypePlaceholder: string;
    referenceId: string;
    referenceIdPlaceholder: string;
    cancel: string;
    start: string;
    history: string;
    currentState: string;
    instanceId: string;
    tenant: string;
    referenceTypeLabel: string;
    referenceIdLabel: string;
    availableTransitions: string;
    noTransitions: string;
    approval: string;
    allCaughtUp: string;
    noPendingApprovals: string;
    colAction: string;
    colTransition: string;
    colInstance: string;
    colStatus: string;
    colActions: string;
    approve: string;
    reject: string;
    delegate: string;
    noTemplates: string;
    noTemplatesHint: string;
    states: string;
    transitions: string;
    stateDiagram: string;
    selectInstanceHint: string;
    goToInstances: string;
    workflowHistory: string;
    cancelWorkflow: string;
    noHistoryEntries: string;
    timeline: string;
  };
  rulesPage: {
    title: string;
    subtitle: string;
    cancel: string;
    newRule: string;
    createRule: string;
    name: string;
    namePlaceholder: string;
    eventType: string;
    eventTypePlaceholder: string;
    priority: string;
    enabled: string;
    conditions: string;
    addCondition: string;
    fieldPlaceholder: string;
    valuePlaceholder: string;
    actions: string;
    remove: string;
    titleLabel: string;
    alertTitlePlaceholder: string;
    messageLabel: string;
    notificationMessagePlaceholder: string;
    roleOptional: string;
    rolePlaceholder: string;
    entityTypeOptional: string;
    entityTypePlaceholder: string;
    messageOptional: string;
    auditLogPlaceholder: string;
    creating: string;
    createRuleButton: string;
    noRulesYet: string;
    noRulesHint: string;
    noActions: string;
    created: string;
    ruleExecutions: string;
    recentExecutionHistory: string;
    noExecutions: string;
    colRule: string;
    colMatched: string;
    colDetail: string;
    colExecutedAt: string;
    matched: string;
    noMatch: string;
    failedToCreateRule: string;
  };
  analyticsPage: {
    title: string;
    subtitle: string;
    tabExecutive: string;
    tabFinancial: string;
    tabOperational: string;
    tabProjects: string;
    businessRecords: string;
    activeProjects: string;
    totalBudget: string;
    documentProcessing: string;
    entityDistribution: string;
    systemHealth: string;
    dataCompleteness: string;
    activeWorkflows: string;
    ruleCoverage: string;
    rulesLabel: string;
    totalProjects: string;
    acrossAllProjects: string;
    processedLabel: string;
    detailsLabel: string;
    totalRevenue: string;
    totalExpenses: string;
    netProfit: string;
    cashPosition: string;
    financialSummary: string;
    accountsReceivable: string;
    accountsPayable: string;
    workingCapital: string;
    budgetVsActual: string;
    documentIntelligence: string;
    budgetLabel: string;
    procurement: string;
    contracts: string;
    documents: string;
    eventsToday: string;
    pendingPrs: string;
    active: string;
    total: string;
    recentActivity: string;
    noRecentEvents: string;
    totalProjectsLabel: string;
    activeLabel: string;
    planning: string;
    completed: string;
    colCode: string;
    colName: string;
    colStatus: string;
    colBudget: string;
  };
  eventsPage: {
    title: string;
    eventsRecorded: string;
    searchPlaceholder: string;
    allEntities: string;
    sortToggleTitle: string;
    sortNewest: string;
    sortOldest: string;
    refresh: string;
    live: string;
    loadingEvents: string;
    retry: string;
    failedToLoad: string;
    noEventsFound: string;
    tryAdjustingFilters: string;
    eventsWillAppear: string;
    entity: string;
    entityId: string;
    severity: string;
  };
  aiCopilot: {
    title: string;
    agentsActive: string;
    tasksCompleted: string;
    tabChat: string;
    tabAgents: string;
    tabActivity: string;
    tabTools: string;
    greeting: string;
    sourcesLabel: string;
    insightsLabel: string;
    risksLabel: string;
    actionsTakenLabel: string;
    suggestionsLabel: string;
    chatPlaceholder: string;
    unableToReach: string;
    suggestApproval: string;
    suggestOverdue: string;
    suggestProjectHealth: string;
    suggestTopSuppliers: string;
    suggestBudgetReport: string;
    suggestRiskAssessment: string;
    totalAgents: string;
    activeNow: string;
    tasksCompletedStat: string;
    avgSuccessRate: string;
    availableTools: string;
    tasksLabel: string;
    successLabel: string;
    toolsLabel: string;
    recentAiActivity: string;
    aiToolRegistry: string;
    aiToolRegistryDesc: string;
    toolAnalytics: string;
    toolAnalyticsDesc: string;
    toolSearch: string;
    toolSearchDesc: string;
    toolReports: string;
    toolReportsDesc: string;
    toolNotifications: string;
    toolNotificationsDesc: string;
    toolWorkflow: string;
    toolWorkflowDesc: string;
    toolDocuments: string;
    toolDocumentsDesc: string;
    toolLedger: string;
    toolLedgerDesc: string;
    toolSuppliers: string;
    toolSuppliersDesc: string;
    toolProjects: string;
    toolProjectsDesc: string;
    toolAutomation: string;
    toolAutomationDesc: string;
    toolIntegration: string;
    toolIntegrationDesc: string;
    toolAudit: string;
    toolAuditDesc: string;
  };
  entityPage: {
    back: string;
    recordsLabel: string;
    fieldsLabel: string;
    dataQuality: string;
    version: string;
    tabOverview: string;
    tabData: string;
    tabDocuments: string;
    tabTimeline: string;
    tabAi: string;
    cancel: string;
    newRecord: string;
    save: string;
    delete: string;
    entityDefinition: string;
    code: string;
    totalRecords: string;
    editableFields: string;
    computedFields: string;
    fieldsSchema: string;
    required: string;
    computed: string;
    relatedEntities: string;
    records: string;
    newRecordTitle: string;
    versionColumn: string;
    actionsColumn: string;
    noRecords: string;
    recordDetails: string;
    documentIntelligence: string;
    documentHint: string;
    uploadDocument: string;
    entityTimeline: string;
    recordCreated: string;
    versionLabel: string;
    noTimelineData: string;
    aiInsightsFor: string;
    aiInsightsSubtitle: string;
    aiAskPlaceholder: string;
    aiAskSuffix: string;
    ask: string;
    showDuplicates: string;
    dataQualityIssues: string;
    trendsOverTime: string;
    anomalies: string;
    confirmDelete: string;
    analysisComplete: string;
    analysisInitializing: string;
    aiEngineConnecting: string;
    createFailed: string;
  };
  workspacePage: {
    askEos: string;
    loadingDashboard: string;
    unifiedDashboard: string;
    dashboardSubtitle: string;
    askPlaceholder: string;
    asking: string;
    aiConnectionError: string;
    activeProjects: string;
    pendingApprovals: string;
    noPendingApprovals: string;
    approveBtn: string;
    latestAlerts: string;
    noNewAlerts: string;
    myTasks: string;
    noActiveTasks: string;
  };
  builderPage: {
    eosBuilder: string;
    subtitle: string;
    objects: string;
    relations: string;
    workflows: string;
    automations: string;
    rules: string;
    permissions: string;
    wizardBasicInfo: string;
    wizardFields: string;
    wizardRelationships: string;
    wizardRules: string;
    wizardWorkflow: string;
    wizardPermissions: string;
    wizardReview: string;
    newObject: string;
    edit: string;
    generate: string;
    del: string;
    system: string;
    fields: string;
    relationsCount: string;
    rulesCount: string;
    workflowsCount: string;
    noDescription: string;
    noObjects: string;
    noObjectsHint: string;
    noRelationsDefined: string;
    noWorkflowsDefined: string;
    trigger: string;
    runs: string;
    statusLabel: string;
    active: string;
    inactive: string;
    noAutomationsDefined: string;
    when: string;
    if: string;
    then: string;
    noRulesDefined: string;
    noRulesHint: string;
    role: string;
    create: string;
    read: string;
    update: string;
    delete: string;
    approve: string;
    noObjectsToConfigure: string;
    noObjectsHintPermissions: string;
    generateTitle: string;
    generateDesc: string;
    databaseTable: string;
    apiEndpoints: string;
    uiForms: string;
    permissionsGen: string;
    workflowGen: string;
    auditTrail: string;
    searchIndex: string;
    aiContext: string;
    generateAll: string;
    createBusinessObject: string;
    basicInformation: string;
    codeLabel: string;
    codeHint: string;
    nameLabel: string;
    typeLabel: string;
    entityType: string;
    documentType: string;
    transactionType: string;
    referenceType: string;
    descriptionLabel: string;
    descriptionPlaceholder: string;
    defineFields: string;
    addField: string;
    required: string;
    unique: string;
    addFieldBtn: string;
    defineRelationships: string;
    addRelationship: string;
    addRelationBtn: string;
    defineRules: string;
    rulesPatternHint: string;
    addRule: string;
    defineWorkflow: string;
    triggerType: string;
    workflowStates: string;
    addState: string;
    workflowHint: string;
    visualFlow: string;
    noStatesDefined: string;
    setPermissions: string;
    permissionsHint: string;
    reviewAndCreate: string;
    unnamed: string;
    willGenerate: string;
    back: string;
    next: string;
    createObject: string;
    cancel: string;
    deleteConfirm: string;
    loadingBuilder: string;
  };
  settingsPage: {
    title: string;
    tabGeneral: string;
    tabAppearance: string;
    tabNotifications: string;
    tabSecurity: string;
    tabIntegrations: string;
    tabBilling: string;
    saved: string;
    companyInformation: string;
    companyName: string;
    taxId: string;
    phone: string;
    email: string;
    website: string;
    address: string;
    regionalSettings: string;
    timezone: string;
    dateFormat: string;
    currency: string;
    language: string;
    theme: string;
    leftToRight: string;
    rightToLeft: string;
    light: string;
    dark: string;
    systemTheme: string;
    notificationChannels: string;
    emailNotifications: string;
    emailNotificationsDesc: string;
    pushNotifications: string;
    pushNotificationsDesc: string;
    smsNotifications: string;
    smsNotificationsDesc: string;
    notificationCategories: string;
    weeklyReports: string;
    projectUpdates: string;
    approvalRequests: string;
    budgetAlerts: string;
    paymentNotifications: string;
    changePassword: string;
    currentPassword: string;
    newPassword: string;
    confirmPassword: string;
    twoFactorAuth: string;
    twoFAViaApp: string;
    useAuthenticatorApp: string;
    enable: string;
    activeSessions: string;
    currentSession: string;
    lastActiveJustNow: string;
    active: string;
    connectedServices: string;
    emailSMTP: string;
    emailSMTPDesc: string;
    smsGateway: string;
    smsGatewayDesc: string;
    paymentGateway: string;
    paymentGatewayDesc: string;
    cloudStorage: string;
    cloudStorageDesc: string;
    accountingSoftware: string;
    accountingSoftwareDesc: string;
    connected: string;
    connect: string;
    currentPlan: string;
    professionalPlan: string;
    planDescription: string;
    usageThisMonth: string;
    users: string;
    aiQueries: string;
    storage: string;
    apiCalls: string;
    paymentHistory: string;
    paid: string;
    saveChanges: string;
    saving: string;
    failedToSave: string;
    passwordsDoNotMatch: string;
    passwordComingSoon: string;
  };
  financialPage: {
    overview: string;
    accounts: string;
    journal: string;
    ledger: string;
    ar: string;
    ap: string;
    payments: string;
    bank: string;
    statements: string;
    ai: string;
    subtitle: string;
    recentEntries: string;
    recentInvoices: string;
    journalEntries: string;
    noJournalEntries: string;
    noInvoices: string;
    chartOfAccounts: string;
    newAccount: string;
    code: string;
    name: string;
    type: string;
    active: string;
    asset: string;
    liability: string;
    equity: string;
    revenue: string;
    expense: string;
    yes: string;
    no_: string;
    noAccounts: string;
    date: string;
    email: string;
    account: string;
    description: string;
    reference: string;
    currency: string;
    status: string;
    back: string;
    doubleEntryLedger: string;
    trialBalance: string;
    fiscalPeriods: string;
    chartOfAccountsTab: string;
    journalEntriesTab: string;
    newLedgerAccount: string;
    accountCode: string;
    accountName: string;
    normalBalance: string;
    debit: string;
    credit: string;
    newJournalEntry: string;
    entryDate: string;
    referenceType: string;
    lines: string;
    addLine: string;
    newFiscalPeriod: string;
    periodName: string;
    startDate: string;
    endDate: string;
    post: string;
    reverse: string;
    total: string;
    noLedgerAccounts: string;
    trialBalanceNotBalanced: string;
    loadingTrialBalance: string;
    close: string;
    noFiscalPeriods: string;
    accountsReceivable: string;
    newCustomer: string;
    newInvoice: string;
    customer: string;
    selectCustomer: string;
    issueDate: string;
    dueDate: string;
    paid: string;
    balanceDue: string;
    tax: string;
    number: string;
    accountsPayable: string;
    newSupplier: string;
    newBill: string;
    supplier: string;
    selectSupplier: string;
    noBills: string;
    bankReconciliation: string;
    newBankAccount: string;
    accountNumber: string;
    bankName: string;
    accountType: string;
    checking: string;
    savings: string;
    creditAccount: string;
    cash: string;
    check: string;
    glAccountId: string;
    noBankAccounts: string;
    reconciliations: string;
    statementBalance: string;
    bookBalance: string;
    difference: string;
    financialStatements: string;
    profitAndLoss: string;
    totalRevenue: string;
    totalExpenses: string;
    netIncome: string;
    balanceSheet: string;
    totalAssets: string;
    totalLiabilities: string;
    totalEquity: string;
    le: string;
    balanceNotBalanced: string;
    arAging: string;
    apAging: string;
    totalOutstanding: string;
    loading: string;
    aiFinancialAnalyst: string;
    aiFinancialDesc: string;
    aiPlaceholder: string;
    ask: string;
    bankTransfer: string;
    select: string;
    customerAR: string;
    supplierAP: string;
  };
  projectsPage: {
    overview: string;
    financial: string;
    budget: string;
    contracts: string;
    procurement: string;
    documents: string;
    timeline: string;
    risks: string;
    approvals: string;
    aiInsights: string;
    budgetStat: string;
    spentStat: string;
    contractsStat: string;
    claimsStat: string;
    procurementStat: string;
    newProject: string;
    cancel: string;
    projectInformation: string;
    code: string;
    name: string;
    client: string;
    location: string;
    manager: string;
    start: string;
    end: string;
    progress: string;
    completion: string;
    budgetUsed: string;
    budgetUtilization: string;
    purchaseRequests: string;
    boqItems: string;
    description: string;
    noClient: string;
    totalBudget: string;
    contractValue: string;
    claimsFiled: string;
    prEstimated: string;
    financialBreakdown: string;
    noContractsLinked: string;
    budgetAllocation: string;
    remaining: string;
    boqSummary: string;
    noBoqItems: string;
    noContractsLinkedToProject: string;
    noPurchaseRequests: string;
    documentIntelligence: string;
    documentHint: string;
    uploadDocument: string;
    viewAll: string;
    projectTimeline: string;
    projectCreated: string;
    contract: string;
    claim: string;
    pr: string;
    budgetOverrun: string;
    claimsPending: string;
    procurementBottleneck: string;
    high: string;
    medium: string;
    low: string;
    action: string;
    pendingApprovals: string;
    approvalsHint: string;
    aiProjectAnalyst: string;
    aiProjectDesc: string;
    aiPlaceholder: string;
    ask: string;
    noProjects: string;
    save: string;
    title: string;
    status: string;
    value: string;
    prNumber: string;
    estCost: string;
  };
  contractsPage: {
    title: string;
    subtitle: string;
    newContract: string;
    noContracts: string;
    backToContracts: string;
    contractsCount: string;
    totalValueLabel: string;
    value: string;
    type: string;
    project: string;
    status: string;
    overview: string;
    financial: string;
    timeline: string;
    documents: string;
    risks: string;
    aiInsights: string;
    contractDetails: string;
    number: string;
    titleField: string;
    counterpartyField: string;
    contractValue: string;
    signed: string;
    completion: string;
    contractHealth: string;
    statusLabel: string;
    contractInGoodStanding: string;
    daysActive: string;
    daysToCompletion: string;
    financialSummary: string;
    invoiced: string;
    remaining: string;
    contractTimeline: string;
    contractCreated: string;
    contractSigned: string;
    expectedCompletion: string;
    notYet: string;
    contractDocuments: string;
    documentsSubtitle: string;
    uploadDocument: string;
    contractExpiry: string;
    valueExposure: string;
    expiresLabel: string;
    noExpirySet: string;
    monitorContractStatus: string;
    reviewFinancialExposure: string;
    contractValueLabel: string;
    aiContractAnalyst: string;
    aiContractDesc: string;
    aiPlaceholder: string;
    ask: string;
    analysisComplete: string;
    analysisInitializing: string;
    aiConnecting: string;
    riskAssessment: string;
    financialAnalysis: string;
    timelineReview: string;
    complianceCheck: string;
    contractNumber: string;
  };
  procurementPage: {
    tabOverview: string;
    tabRequests: string;
    tabSuppliers: string;
    tabOrders: string;
    tabAnalysis: string;
    tabAi: string;
    newRequest: string;
    cancel: string;
    save: string;
    totalRequests: string;
    draft: string;
    approved: string;
    ordered: string;
    priorityDistribution: string;
    recentRequests: string;
    noProcurementRequests: string;
    requisition: string;
    title: string;
    priority: string;
    status: string;
    details: string;
    estValue: string;
    noRequests: string;
    newProcurementRequest: string;
    requisitionNumber: string;
    low: string;
    medium: string;
    high: string;
    urgent: string;
    supplierManagement: string;
    supplierManagementDesc: string;
    purchaseOrders: string;
    purchaseOrdersDesc: string;
    totalValue: string;
    avgPerRequest: string;
    pending: string;
    aiProcurementAdvisor: string;
    aiProcurementDesc: string;
    aiPlaceholder: string;
    ask: string;
    analysisComplete: string;
    analysisInitializing: string;
    aiConnecting: string;
  };
  notificationsPage: {
    title: string;
    subtitle: string;
    errorLoading: string;
    errorMarkRead: string;
    errorMarkAllRead: string;
    justNow: string;
    minutesAgo: string;
    hoursAgo: string;
    daysAgo: string;
    unreadLabel: string;
    markAllRead: string;
    statsTotal: string;
    statsUnread: string;
    statsToday: string;
    statsThisWeek: string;
    filterAll: string;
    filterUnread: string;
    filterApprovals: string;
    filterSystem: string;
    filterAlerts: string;
    noNotifications: string;
    allCaughtUp: string;
    relatedEntity: string;
    viewRelated: string;
    markAsRead: string;
    dismiss: string;
  };
  auditPage: {
    title: string;
    actionLabel: string;
    filterByAction: string;
    resourceType: string;
    filterByResource: string;
    clear: string;
    action: string;
    resourceId: string;
    actor: string;
    timestamp: string;
    details: string;
    view: string;
  };
  documentsPage: {
    loading: string;
    title: string;
    documentsCount: string;
    total: string;
    processed: string;
    processing: string;
    failed: string;
    categories: string;
    searchPlaceholder: string;
    allCategories: string;
    invoice: string;
    receipt: string;
    contract: string;
    purchaseOrder: string;
    goodsReceived: string;
    report: string;
    other: string;
    search: string;
    file: string;
    category: string;
    status: string;
    classification: string;
    size: string;
    actions: string;
    extract: string;
    classify: string;
    po: string;
    noDocumentsFound: string;
    categoryLabel: string;
    statusLabel: string;
    typeLabel: string;
    mimeLabel: string;
    extractedData: string;
    ocrText: string;
  };
  boqPage: {
    title: string;
    subtitle: string;
    createBoq: string;
    editBoq: string;
    contract: string;
    contractRequired: string;
    selectContract: string;
    version: string;
    status: string;
    draft: string;
    submitted: string;
    approved: string;
    confirm: string;
    areYouSure: string;
    failedToLoad: string;
    failedToSave: string;
  };
  claimsPage: {
    editClaim: string;
    createClaim: string;
    claimNumber: string;
    contract: string;
    selectContract: string;
    claimDate: string;
    periodStart: string;
    periodEnd: string;
  };
  reportsPage: {
    reportType: string;
    exportFormat: string;
    generateReport: string;
    exportCsv: string;
    exportExcel: string;
    exportPdf: string;
    financialSummary: string;
    profitLoss: string;
    trialBalance: string;
    accountBalances: string;
    projects: string;
    claims: string;
  };
  sdkPage: {
    title: string;
    subtitle: string;
    newApp: string;
    apiKey: string;
    totalEvents: string;
    pending: string;
    processed: string;
    failed: string;
    apps: string;
    apiKeys: string;
    webhooks: string;
    events: string;
    name: string;
    keyPrefix: string;
    uses: string;
    status: string;
    active: string;
    revoked: string;
    noApiKeys: string;
    event: string;
    url: string;
    triggers: string;
    noWebhooks: string;
    eventsDashboard: string;
    newSdkApp: string;
    code: string;
    plugin: string;
    connector: string;
    widget: string;
    automation: string;
    cancel: string;
    create: string;
    generateApiKey: string;
    keyName: string;
    generateKey: string;
    noAppsRegistered: string;
    loading: string;
  };
  catalogPage: {
    eyebrow: string;
    title: string;
    subtitle: string;
    signOut: string;
    publishedEntities: string;
    available: string;
    newEntity: string;
    refresh: string;
    loading: string;
    noEntities: string;
    fields: string;
  };
  marketplacePage: {
    title: string;
    subtitle: string;
    apps: string;
    categories: string;
    installs: string;
    reviews: string;
    searchPlaceholder: string;
    allCategories: string;
    search: string;
    featured: string;
    noDescription: string;
    noAppsFound: string;
    tryAdjusting: string;
    free: string;
    freemium: string;
    loading: string;
    globalizationPage: string;
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
    home: 'Home',
    businessObjects: 'Business Objects',
    businessGraph: 'Business Graph',
    workflows: 'Workflows',
    rules: 'Rules',
    events: 'Events',
    analytics: 'Analytics',
    aiCopilot: 'AI Copilot',
    documents: 'Documents',
    integrations: 'Integrations',
    globalization: 'Globalization',
    builder: 'Builder',
    developerSdk: 'Developer SDK',
    marketplace: 'Marketplace',
    workspace: 'Workspace',
    overview: 'Overview',
    tenants: 'Tenants',
    rolesPermissions: 'Roles & Permissions',
    plans: 'Plans',
    billing: 'Billing',
    featureFlags: 'Feature Flags',
    aiControlCenter: 'AI Control Center',
    automation: 'Automation',
    applications: 'Applications',
    apiManagement: 'API Management',
    securityCenter: 'Security Center',
    auditLogs: 'Audit Logs',
    systemHealth: 'System Health',
    backupRecovery: 'Backup & Recovery',
    support: 'Support',
    search: 'Search',
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
    systemHealth: 'System Health',
    allSystems: 'All Systems',
    revenueGrowth: 'Revenue Growth',
    tenantGrowth: 'Tenant Growth',
    userGrowth: 'User Growth',
    aiUsage: 'AI Usage',
    operational: 'Operational',
    warning: 'Warning',
    critical: 'Critical',
    newTenantRegistered: 'New tenant registered',
    paymentProcessed: 'Payment processed',
    aiModelUpdated: 'AI model updated',
    userSuspended: 'User suspended',
    backupCompleted: 'Backup completed',
    minutesAgo: 'minutes ago',
    hoursAgo: 'hours ago',
    daysAgo: 'days ago',
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
    titleField: 'Title',
    counterparty: 'Counterparty',
    totalAmount: 'Total Amount',
    status: 'Status',
    draft: 'Draft',
    pendingApproval: 'Pending Approval',
    active: 'Active',
    completed: 'Completed',
    terminated: 'Terminated',
    signedDate: 'Signed Date',
    completionDate: 'Completion Date',
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
    date: 'Date',
    period: 'Period',
    pending: 'Pending',
    draft: 'Draft',
    submitted: 'Submitted',
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
    requisitionNumber: 'Requisition Number',
    project: 'Project',
    priority: 'Priority',
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    urgent: 'Urgent',
    draft: 'Draft',
    pendingApproval: 'Pending Approval',
    approved: 'Approved',
    ordered: 'Ordered',
    received: 'Received',
    invoiced: 'Invoiced',
    paid: 'Paid',
    cancelled: 'Cancelled',
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
    skip: 'Skip',
  },
  landing: {
    features: 'Features',
    pricing: 'Pricing',
    docs: 'Docs',
    signIn: 'Sign In',
    heroTitle1: 'Your Business,',
    heroTitle2: 'One System',
    heroSubtitle: '2TO EOS is an AI-native Business Operating System that turns your business model, data, rules, workflows, and financial reality into one intelligent platform.',
    startTrial: 'Start Free Trial',
    watchDemo: 'Watch Demo',
    problemTitle: 'Your company runs on 12 different tools',
    solutionTitle: 'One platform to run it all',
    solutionSubtitle: '2TO EOS replaces your entire software stack with one intelligent, AI-native platform.',
    ctaTitle: 'Ready to transform your business?',
    ctaSubtitle: 'Join hundreds of companies already using 2TO EOS.',
    getStarted: 'Get Started',
    learnMore: 'Learn More',
    tools: ['Accounting', 'Excel', 'WhatsApp', 'CRM', 'HR', 'Inventory', 'Email', 'Banking', 'Documents', 'Projects', 'BI', 'Portals'],
    footerRights: '© 2026 2TO. All rights reserved.',
  },
  login: {
    backToHome: 'Back to Home',
    title: '2TO EOS',
    subtitle: 'Business Operating System',
    emailLabel: 'Email',
    passwordLabel: 'Password',
    signIn: 'Sign in',
    signingIn: 'Signing in...',
    noAccount: "Don't have an account?",
    createWorkspace: 'Create a new workspace',
  },
  onboard: {
    welcomeTitle: 'Welcome to EOS',
    welcomeSubtitle: "Your AI-native Business Operating System. Let's set up your workspace in a few steps.",
    getStarted: 'Get Started',
    companyName: 'Company Name',
    companyNamePlaceholder: 'e.g. Acme Corp',
    industry: 'Industry',
    industryPlaceholder: 'e.g. Technology, Construction...',
    inviteTeam: 'Invite Team Members',
    invitePlaceholder: 'Enter email addresses separated by commas',
    completeTitle: "You're all set!",
    completeSubtitle: 'Your workspace is ready. Start exploring your new ERP system.',
    goToDashboard: 'Go to Dashboard',
  },
  sidebar: {
    platform: 'Platform',
    erp: 'ERP',
    administration: 'Administration',
    master: 'Master',
  },
  adminSidebar: {
    eosControlCenter: 'EOS Control Center',
    systemOwner: 'System Owner',
    superAdmin: 'Super Admin',
    featureFlags: 'Feature Flags',
    securityCenter: 'Security Center',
    auditLogs: 'Audit Logs',
    systemHealth: 'System Health',
    systemSettings: 'System Settings',
    globalSearch: 'Global Search',
    notificationsCenter: 'Notifications',
    backupRecovery: 'Backup & Recovery',
    apiManagement: 'API Management',
    automationCenter: 'Automation',
    supportCenter: 'Support',
    applications: 'Applications',
    integrationsHub: 'Integrations',
    master: 'Master',
    overview: 'Overview',
    groupOrganization: 'Organization',
    groupCommerce: 'Commerce',
    groupPlatform: 'Platform',
    groupAi: 'AI',
    groupAutomation: 'Automation',
    groupSecurity: 'Security',
    groupSystem: 'System',
    groupSupport: 'Support',
    groupMaster: 'Master',
    tenants: 'Tenants',
    users: 'Users',
    rolesPermissions: 'Roles & Permissions',
    plans: 'Plans',
    subscriptions: 'Subscriptions',
    billing: 'Billing',
    transactions: 'Transactions',
    aiControlCenter: 'AI Control Center',
    aiModels: 'AI Models',
    aiWorkforce: 'AI Workforce',
    aiUsage: 'AI Usage',
    workflows: 'Workflows',
    automations: 'Automations',
    jobs: 'Jobs',
    sessions: 'Sessions',
    monitoring: 'Monitoring',
    tickets: 'Tickets',
    supportPage: 'Support',
  },
  adminHeader: {
    quickActions: 'Quick Actions',
    newTenant: 'New Tenant',
    newUser: 'New User',
    newPlan: 'New Plan',
    newRole: 'New Role',
    newApiKey: 'New API Key',
    newAiAgent: 'New AI Agent',
    disableSystem: 'Disable System',
    notifications: 'Notifications',
    searchPlaceholder: 'Search tenants, users, invoices, API keys...',
    confirmDangerousAction: 'Confirm Dangerous Action',
    confirmDangerousMessage: 'This action can cause system-wide disruption. Are you sure?',
  },
  master: {
    title: 'Master Control Center',
    subtitle: 'Full Platform Control Center',
    overview: {
      title: 'Overview',
      totalTenants: 'Total Tenants',
      activeTenants: 'Active Tenants',
      suspendedTenants: 'Suspended Tenants',
      totalUsers: 'Total Users',
      activeUsers: 'Active Users',
      newTenants: 'New Tenants',
      mrr: 'Monthly Revenue',
      arr: 'Annual Revenue',
      revenue: 'Revenue',
      outstandingPayments: 'Outstanding Payments',
      aiUsage: 'AI Usage',
      apiUsage: 'API Usage',
      automationRuns: 'Automation Runs',
      storageUsage: 'Storage Usage',
      analyticsTab: 'Analytics',
    },
    health: {
      title: 'System Health',
      apiStatus: 'API Status',
      databaseStatus: 'Database Status',
      aiServicesStatus: 'AI Services',
      backgroundJobs: 'Background Jobs',
      queueStatus: 'Queue Status',
      storageStatus: 'Storage Status',
      emailService: 'Email Service',
      paymentGateway: 'Payment Gateway',
      externalIntegrations: 'External Integrations',
      aiServices: 'AI Services',
      storage: 'Storage',
      integrations: 'Integrations',
      cpu: 'CPU',
      ram: 'RAM',
      disk: 'Disk Usage',
      database: 'Database Latency',
      apiLatency: 'API Latency',
      requestsPerSec: 'Requests / sec',
      errorRate: 'Error Rate',
      queue: 'Queue Depth',
      operational: 'Operational',
      warning: 'Warning',
      critical: 'Critical',
      offline: 'Offline',
    },
    tenants: {
      title: 'Tenant Management',
      searchPlaceholder: 'Search tenants...',
      companyName: 'Company',
      owner: 'Owner',
      industry: 'Industry',
      country: 'Country',
      plan: 'Plan',
      status: 'Status',
      users: 'Users',
      storage: 'Storage',
      aiUsage: 'AI Usage',
      createdAt: 'Created',
      lastActivity: 'Last Activity',
      actions: 'Actions',
      view: 'View',
      edit: 'Edit',
      suspend: 'Suspend',
      activate: 'Activate',
      delete: 'Delete',
      impersonate: 'Impersonate',
      changePlan: 'Change Plan',
    },
    users: {
      title: 'User Management',
      searchPlaceholder: 'Search users...',
      user: 'User',
      email: 'Email',
      tenant: 'Tenant',
      role: 'Role',
      status: 'Status',
      mfa: 'MFA',
      lastLogin: 'Last Login',
      created: 'Created',
      sessions: 'Sessions',
      riskStatus: 'Risk',
      actions: 'Actions',
      view: 'View',
      edit: 'Edit',
      suspend: 'Suspend',
      activate: 'Activate',
      resetPassword: 'Reset Password',
      forceLogout: 'Force Logout',
      resetMFA: 'Reset MFA',
      delete: 'Delete',
    },
    roles: {
      title: 'Roles & Permissions',
      systemRoles: 'System Roles',
      tenantRoles: 'Tenant Roles',
      customRoles: 'Custom Roles',
      permissions: 'Permissions',
      permissionGroups: 'Permission Groups',
    },
    plans: {
      title: 'Subscription Plans',
      pricing: 'Pricing',
      features: 'Features',
      limits: 'Limits',
      trialPeriod: 'Trial Period',
      usageLimits: 'Usage Limits',
      aiLimits: 'AI Limits',
      storageLimits: 'Storage Limits',
      userLimits: 'User Limits',
      apiLimits: 'API Limits',
      actions: {
        createPlan: 'Create Plan',
        editPlan: 'Edit Plan',
        duplicatePlan: 'Duplicate Plan',
        archivePlan: 'Archive Plan',
        changePricing: 'Change Pricing',
        configureFeatures: 'Configure Features',
      },
    },
    billing: {
      title: 'Billing & Revenue',
      revenue: 'Revenue',
      mrr: 'MRR',
      arr: 'ARR',
      invoices: 'Invoices',
      payments: 'Payments',
      failedPayments: 'Failed Payments',
      refunds: 'Refunds',
      taxes: 'Taxes',
      transactions: 'Transactions',
    },
    featureFlags: {
      title: 'Feature Flags',
      erp: 'ERP',
      aiWorkforce: 'AI Workforce',
      automation: 'Automation',
      analytics: 'Analytics',
      industryOS: 'Industry OS',
      advancedReports: 'Advanced Reports',
      api: 'API',
      integrations: 'Integrations',
      global: 'Global',
      byPlan: 'By Plan',
      byTenant: 'By Tenant',
      byUser: 'By User',
      enable: 'Enable',
      disable: 'Disable',
      rolloutPercent: 'Rollout %',
    },
    aiControl: {
      title: 'AI Control Center',
      models: 'Models',
      providers: 'Providers',
      modelUsage: 'Model Usage',
      tokenUsage: 'Token Usage',
      cost: 'Cost',
      requests: 'Requests',
      latency: 'Latency',
      errors: 'Errors',
      aiAgents: 'AI Agents',
      aiWorkforce: 'AI Workforce',
      promptManagement: 'Prompt Management',
      aiPolicies: 'AI Policies',
      modelRouting: 'Model Routing',
      modelManagement: {
        provider: 'Provider',
        modelName: 'Model Name',
        status: 'Status',
        cost: 'Cost',
        contextWindow: 'Context Window',
        rateLimits: 'Rate Limits',
        default: 'Default',
        backup: 'Fallback',
        enable: 'Enable',
        disable: 'Disable',
        configure: 'Configure',
        setDefault: 'Set Default',
        setFallback: 'Set Fallback',
      },
    },
    automation: {
      title: 'Automation Center',
      workflows: 'Workflows',
      automations: 'Automations',
      jobs: 'Jobs',
      automationName: 'Automation Name',
      tenant: 'Tenant',
      trigger: 'Trigger',
      status: 'Status',
      executions: 'Executions',
      successRate: 'Success Rate',
      errors: 'Errors',
      lastRun: 'Last Run',
      actions: {
        enable: 'Enable',
        disable: 'Disable',
        edit: 'Edit',
        duplicate: 'Duplicate',
        test: 'Test',
        viewLogs: 'View Logs',
      },
    },
    integrations: {
      title: 'Integration Hub',
      payment: 'Payment',
      email: 'Email',
      sms: 'SMS',
      whatsapp: 'WhatsApp',
      accounting: 'Accounting',
      crm: 'CRM',
      storage: 'Storage',
      aiProviders: 'AI Providers',
      webhooks: 'Webhooks',
      apis: 'APIs',
      integration: 'Integration',
      provider: 'Provider',
      connectedTenants: 'Connected Tenants',
      errors: 'Errors',
      lastSync: 'Last Sync',
    },
    api: {
      title: 'API Management',
      apiKeys: 'API Keys',
      apiClients: 'API Clients',
      requests: 'Requests',
      rateLimits: 'Rate Limits',
      webhooks: 'Webhooks',
      apiErrors: 'API Errors',
      apiUsage: 'API Usage',
      createApiKey: 'Create API Key',
      revoke: 'Revoke',
      rotate: 'Rotate',
      setPermissions: 'Set Permissions',
      setRateLimits: 'Set Rate Limits',
    },
    security: {
      title: 'Security Center',
      loginAttempts: 'Login Attempts',
      failedLogins: 'Failed Logins',
      suspiciousActivity: 'Suspicious Activity',
      activeSessions: 'Active Sessions',
      mfaStatus: 'MFA Status',
      securityEvents: 'Security Events',
      ipActivity: 'IP Activity',
      apiSecurity: 'API Security',
      accessViolations: 'Access Violations',
      forceLogout: 'Force Logout',
      blockIP: 'Block IP',
      revokeToken: 'Revoke Token',
      disableAccount: 'Disable Account',
      requireMFA: 'Require MFA',
    },
    auditLogs: {
      title: 'Audit Logs',
      user: 'User',
      tenant: 'Tenant',
      action: 'Action',
      resource: 'Resource',
      timestamp: 'Timestamp',
      ip: 'IP',
      device: 'Device',
      result: 'Result',
      filters: {
        date: 'Date',
        user: 'User',
        tenant: 'Tenant',
        action: 'Action',
        resource: 'Resource',
        ip: 'IP',
        success: 'Success',
        failure: 'Failure',
      },
    },
    systemHealth: {
      title: 'System Health & Monitoring',
      cpu: 'CPU',
      ram: 'RAM',
      disk: 'Disk',
      database: 'Database',
      apiLatency: 'API Latency',
      requestsPerSec: 'Requests/sec',
      errorRate: 'Error Rate',
      queue: 'Queue',
      backgroundJobs: 'Background Jobs',
      activeIncidents: 'Active Incidents',
      warnings: 'Warnings',
      resolvedIncidents: 'Resolved Incidents',
    },
    backups: {
      title: 'Backup & Recovery',
      databaseBackups: 'Database Backups',
      fileBackups: 'File Backups',
      backupSchedule: 'Backup Schedule',
      backupStatus: 'Backup Status',
      restorePoints: 'Restore Points',
      createBackup: 'Create Backup',
      restore: 'Restore',
      download: 'Download',
      delete: 'Delete',
      configureSchedule: 'Configure Schedule',
    },
    notifications: {
      title: 'Notifications Center',
      global: 'Global',
      tenantSpecific: 'Tenant-specific',
      userSpecific: 'User-specific',
      announcement: 'Announcement',
      maintenance: 'Maintenance',
      security: 'Security',
      billing: 'Billing',
      systemAlert: 'System Alert',
    },
    support: {
      title: 'Support Center',
      supportTickets: 'Support Tickets',
      tenantIssues: 'Tenant Issues',
      userIssues: 'User Issues',
      systemIssues: 'System Issues',
      ticket: 'Ticket',
      priority: 'Priority',
      status: 'Status',
      assignedTo: 'Assigned To',
      created: 'Created',
      updated: 'Updated',
    },
    quickActions: {
      create: 'Create',
      newTenant: 'New Tenant',
      newUser: 'New User',
      newPlan: 'New Plan',
      newRole: 'New Role',
      newFeature: 'New Feature',
      newNotification: 'New Notification',
      newApiKey: 'New API Key',
      newAiAgent: 'New AI Agent',
    },
    settings: {
      general: 'General',
      email: 'Email',
      notifications: 'Notifications',
      security: 'Security',
      system: 'System',
      ai: 'AI',
    },
    common: {
      loading: 'Loading...',
      search: 'Search...',
      noData: 'No data found',
      total: 'Total',
      actions: 'Actions',
      view: 'View',
      edit: 'Edit',
      delete: 'Delete',
      suspend: 'Suspend',
      activate: 'Activate',
      enable: 'Enable',
      disable: 'Disable',
      confirm: 'Confirm',
      cancel: 'Cancel',
      save: 'Save',
      close: 'Close',
      create: 'Create',
      new: 'New',
      filter: 'Filter',
      all: 'All',
      success: 'Success',
      failed: 'Failed',
      warning: 'Warning',
      active: 'Active',
      inactive: 'Inactive',
      back: 'Back',
      next: 'Next',
      export: 'Export',
      import: 'Import',
      download: 'Download',
      upload: 'Upload',
      refresh: 'Refresh',
      retry: 'Retry',
      createdAt: 'Created',
      updatedAt: 'Updated',
      lastActive: 'Last Active',
    },
  },
  applications: {
    title: 'Applications',
    subtitle: 'Manage platform applications and modules',
    tenants: 'tenants',
  },
  globalSearch: {
    title: 'Global Search',
    subtitle: 'Search across all system resources',
    searchPlaceholder: 'Search tenants, users, invoices, API keys...',
  },
  integrationsHub: {
    title: 'Integrations Hub',
    subtitle: 'Manage all external system connections',
    lastSync: 'Last sync',
    configure: 'Configure',
    realtime: 'Real-time',
    tenants: 'tenants',
  },
  systemHealth: {
    title: 'System Health & Monitoring',
    subtitle: 'Real-time infrastructure monitoring',
    systemIncidents: 'System Incidents',
    backgroundJobs: 'Background Jobs',
    elevatedDisk: 'Elevated disk usage on node-3',
    queueBacklog: 'Queue backlog detected',
    scheduledMaintenance: 'Scheduled maintenance',
    dailyBackup: 'Daily Backup',
    aiModelTraining: 'AI Model Training',
    emailDispatch: 'Email Dispatch',
    reportGeneration: 'Report Generation',
  },
  systemSettings: {
    title: 'System Settings',
    subtitle: 'Platform-wide configuration',
    saveChanges: 'Save Changes',
    generalTab: 'General',
    emailTab: 'Email',
    notificationsTab: 'Notifications',
    securityTab: 'Security',
    systemTab: 'System',
    aiTab: 'AI',
    platformName: 'Platform Name',
    defaultLanguage: 'Default Language',
    timezone: 'Timezone',
    defaultCurrency: 'Default Currency',
    smtpHost: 'SMTP Host',
    senderEmail: 'Sender Email',
    templates: 'Templates',
    emailNotifications: 'Email Notifications',
    pushNotifications: 'Push Notifications',
    smsAlerts: 'SMS Alerts',
    sessionTimeout: 'Session Timeout',
    passwordMinLength: 'Password Min Length',
    mfaRequired: 'MFA Required',
    maintenanceMode: 'Maintenance Mode',
    debugMode: 'Debug Mode',
    cacheDuration: 'Cache Duration',
    defaultModel: 'Default Model',
    fallbackModel: 'Fallback Model',
    tokenLimit: 'Token Limit',
  },
  securityCenter: {
    title: 'Security Center',
    subtitle: 'Monitor security events, active sessions, and threats',
    recentEvents: 'Recent Security Events',
    type: 'Type',
    user: 'User',
    ip: 'IP',
    result: 'Result',
    time: 'Time',
    device: 'Device',
  },
  notificationsCenter: {
    title: 'Notifications Center',
    subtitle: 'Send global, tenant-specific, or user-specific notifications',
    sendNotification: 'Send Notification',
    notificationTitle: 'Notification title',
    message: 'Message',
    scope: 'Scope',
    category: 'Category',
    send: 'Send',
  },
  backupRecovery: {
    title: 'Backup & Recovery',
    subtitle: 'Database backups, file backups, and restore points',
    lastBackup: 'Last Backup',
    totalBackups: 'Total Backups',
    createBackup: 'Create Backup',
    restore: 'Restore',
    id: 'ID',
    type: 'Type',
    size: 'Size',
    status: 'Status',
    date: 'Date',
    duration: 'Duration',
  },
  apiManagement: {
    title: 'API Management',
    subtitle: 'Manage API keys, clients, and rate limits',
    totalRequests: 'Total Requests',
    activeKeys: 'Active Keys',
    createApiKey: 'Create API Key',
    key: 'Key',
    name: 'Name',
    tenant: 'Tenant',
    requests: 'Requests',
    rateLimit: 'Rate Limit',
    rotate: 'Rotate',
    revoke: 'Revoke',
  },
  automationCenter: {
    title: 'Automation Center',
    subtitle: 'Manage workflows and automations',
    newAutomation: 'New Automation',
    name: 'Name',
    tenant: 'Tenant',
    trigger: 'Trigger',
    executions: 'Executions',
    successRate: 'Success Rate',
    lastRun: 'Last Run',
    running: 'Running',
    paused: 'Paused',
    failed: 'Failed',
  },
  supportCenter: {
    title: 'Support Center',
    subtitle: 'Manage support tickets and issues',
    newTicket: 'New Ticket',
    ticket: 'Ticket',
    tenant: 'Tenant',
    priority: 'Priority',
    assigned: 'Assigned',
    created: 'Created',
    open: 'Open',
    inProgress: 'In Progress',
    resolved: 'Resolved',
  },
  executiveDashboard: {
    searchPlaceholder: 'Search projects, suppliers, documents, or ask EOS anything...',
    workspace: 'Workspace',
    whatNeedsAttention: 'What needs your attention today',
    askEos: 'Ask EOS',
    askEosSubtitle: 'Ask anything about your business — analyze, act, automate',
    askEosPlaceholder: 'e.g. Show overdue invoices, What\'s the project margin, List suppliers exceeding budget...',
    analyzing: 'Analyzing...',
    analysisComplete: 'Analysis complete.',
    aiFallbackResponse: 'I can help with projects, finances, procurement, approvals, and supplier analysis. Try asking about budget overruns or overdue invoices.',
    suggestApproval: 'What needs my approval?',
    suggestOverdue: 'Show overdue invoices',
    suggestArAging: 'AR aging summary',
    suggestProjectHealth: 'Project health summary',
    suggestTopSuppliers: 'Top suppliers by spend',
    suggestBudgetReport: 'Budget utilization report',
    statRecords: 'Records',
    statApprovals: 'Approvals',
    statWorkflows: 'Workflows',
    statArOutstanding: 'AR Outstanding',
    statApOutstanding: 'AP Outstanding',
    statDocuments: 'Documents',
    tabOverview: 'Overview',
    tabAttention: 'Attention',
    tabFinancial: 'Financial',
    tabRisks: 'Risks',
    tabActivity: 'Activity',
    quickNavigation: 'Quick Navigation',
    businessObjects: 'Business Objects',
    noDataYet: 'No data yet.',
    recentEvents: 'Recent Events',
    noEventsYet: 'No events yet.',
    pendingApprovals: 'Pending Approvals',
    approve: 'Approve',
    reject: 'Reject',
    allClearNoApprovals: 'All clear! No pending approvals.',
    overdueInvoices: 'Overdue Invoices',
    due: 'Due',
    noOverdueInvoices: 'No overdue invoices',
    overdueBills: 'Overdue Bills',
    noOverdueBills: 'No overdue bills',
    activeWorkflows: 'Active Workflows',
    state: 'State',
    noActiveWorkflows: 'No active workflows',
    arAging: 'AR Aging',
    apAging: 'AP Aging',
    current: 'Current',
    totalAr: 'Total AR',
    totalAp: 'Total AP',
    noData: 'No data',
    recentInvoices: 'Recent Invoices',
    noInvoices: 'No invoices',
    dueAmount: 'due',
    recentBills: 'Recent Bills',
    noBills: 'No bills',
    noDetectedRisks: 'No detected risks',
    allSystemsNormal: 'All systems operating normally',
    ruleActivity: 'Rule Activity',
    noRuleFirings: 'No rule firings yet.',
    documentIntelligence: 'Document Intelligence',
    docTotal: 'Total',
    docProcessed: 'Processed',
    docProcessing: 'Processing',
    docFailed: 'Failed',
    activeProjects: 'Active Projects',
    noClient: 'No client',
    budgetSuffix: 'budget',
    actionLabel: 'Action',
  },
  businessObjectsExplorer: {
    title: 'Business Objects',
    publishedEntities: 'published entities',
    searchPlaceholder: 'Search entities...',
    fields: 'fields',
    noObjectsFound: 'No business objects found.',
    publishHint: 'Publish entities via the Metadata API to see them here.',
  },
  businessGraph: {
    title: 'Business Graph',
    subtitle: 'Explore how your business objects connect — every entity tells a story',
    entityType: 'Entity Type',
    record: 'Record',
    depth: 'Depth',
    loading: 'Loading...',
    noRecords: 'No records',
    refreshGraph: 'Refresh Graph',
    nodes: 'Nodes',
    edges: 'Edges',
    entityTypes: 'Entity Types',
    entryNode: 'Entry Node',
    entity: 'Entity',
    titleLabel: 'Title',
    recordId: 'Record ID',
    selectToVisualize: 'Select an entity and record to visualize the business graph.',
    nodeDetails: 'Node Details',
    connections: 'Connections',
    data: 'Data',
    entityLegend: 'Entity Legend',
  },
  workflowsPage: {
    title: 'Workflows',
    subtitle: 'Manage workflow instances, approvals, and templates',
    tabInstances: 'Instances',
    tabApprovals: 'Approvals',
    tabTemplates: 'Templates',
    tabHistory: 'History',
    startWorkflow: 'Start Workflow',
    refresh: 'Refresh',
    noInstances: 'No workflow instances',
    noInstancesHint: 'Workflows will appear here once they are started.',
    startNewWorkflow: 'Start New Workflow',
    template: 'Template',
    selectTemplate: 'Select a template...',
    referenceType: 'Reference Type',
    referenceTypePlaceholder: 'e.g. expense, purchase_order',
    referenceId: 'Reference ID',
    referenceIdPlaceholder: 'e.g. exp_12345',
    cancel: 'Cancel',
    start: 'Start',
    history: 'History',
    currentState: 'Current state',
    instanceId: 'Instance ID',
    tenant: 'Tenant',
    referenceTypeLabel: 'Reference Type',
    referenceIdLabel: 'Reference ID',
    availableTransitions: 'Available Transitions',
    noTransitions: 'No transitions available for this state.',
    approval: 'approval',
    allCaughtUp: 'All caught up',
    noPendingApprovals: 'No pending approvals at the moment.',
    colAction: 'Action',
    colTransition: 'Transition',
    colInstance: 'Instance',
    colStatus: 'Status',
    colActions: 'Actions',
    approve: 'Approve',
    reject: 'Reject',
    delegate: 'Delegate',
    noTemplates: 'No templates',
    noTemplatesHint: 'Workflow templates will appear here.',
    states: 'States',
    transitions: 'Transitions',
    stateDiagram: 'State Diagram',
    selectInstanceHint: 'Select an instance from the Instances tab to view its history.',
    goToInstances: 'Go to Instances',
    workflowHistory: 'Workflow History',
    cancelWorkflow: 'Cancel Workflow',
    noHistoryEntries: 'No history entries yet.',
    timeline: 'Timeline',
  },
  rulesPage: {
    title: 'Rules',
    subtitle: 'Automation rules that react to platform events',
    cancel: 'Cancel',
    newRule: 'New Rule',
    createRule: 'Create Rule',
    name: 'Name',
    namePlaceholder: 'e.g. Flag high-value purchase',
    eventType: 'Event Type',
    eventTypePlaceholder: 'purchase_request.created',
    priority: 'Priority',
    enabled: 'Enabled',
    conditions: 'Conditions',
    addCondition: '+ Add Condition',
    fieldPlaceholder: 'field (e.g. payload.amount)',
    valuePlaceholder: 'value',
    actions: 'Actions',
    remove: 'Remove',
    titleLabel: 'Title',
    alertTitlePlaceholder: 'Alert title',
    messageLabel: 'Message',
    notificationMessagePlaceholder: 'Notification message',
    roleOptional: 'Role (optional)',
    rolePlaceholder: 'e.g. manager',
    entityTypeOptional: 'Entity Type (optional)',
    entityTypePlaceholder: 'e.g. purchase_request',
    messageOptional: 'Message (optional)',
    auditLogPlaceholder: 'Audit log message',
    creating: 'Creating\u2026',
    createRuleButton: 'Create Rule',
    noRulesYet: 'No rules yet',
    noRulesHint: 'Rules will appear here once they are created.',
    noActions: 'No actions',
    created: 'Created',
    ruleExecutions: 'Rule Executions',
    recentExecutionHistory: 'Recent rule execution history',
    noExecutions: 'No executions recorded yet.',
    colRule: 'Rule',
    colMatched: 'Matched',
    colDetail: 'Detail',
    colExecutedAt: 'Executed At',
    matched: 'Matched',
    noMatch: 'No match',
    failedToCreateRule: 'Failed to create rule',
  },
  analyticsPage: {
    title: 'Analytics',
    subtitle: 'Executive insights with drill-down capability',
    tabExecutive: 'Executive',
    tabFinancial: 'Financial',
    tabOperational: 'Operational',
    tabProjects: 'Projects',
    businessRecords: 'Business Records',
    activeProjects: 'Active Projects',
    totalBudget: 'Total Budget',
    documentProcessing: 'Document Processing',
    entityDistribution: 'Entity Distribution',
    systemHealth: 'System Health',
    dataCompleteness: 'Data Completeness',
    activeWorkflows: 'Active Workflows',
    ruleCoverage: 'Rule Coverage',
    rulesLabel: 'rules',
    totalProjects: 'total projects',
    acrossAllProjects: 'Across all projects',
    processedLabel: 'processed',
    detailsLabel: 'details',
    totalRevenue: 'Total Revenue',
    totalExpenses: 'Total Expenses',
    netProfit: 'Net Profit',
    cashPosition: 'Cash Position',
    financialSummary: 'Financial Summary',
    accountsReceivable: 'Accounts Receivable',
    accountsPayable: 'Accounts Payable',
    workingCapital: 'Working Capital',
    budgetVsActual: 'Budget vs Actual',
    documentIntelligence: 'Document Intelligence',
    budgetLabel: 'budget',
    procurement: 'Procurement',
    contracts: 'Contracts',
    documents: 'Documents',
    eventsToday: 'Events Today',
    pendingPrs: 'pending PRs',
    active: 'active',
    total: 'total',
    recentActivity: 'Recent Activity',
    noRecentEvents: 'No recent events',
    totalProjectsLabel: 'Total Projects',
    activeLabel: 'Active',
    planning: 'Planning',
    completed: 'Completed',
    colCode: 'Code',
    colName: 'Name',
    colStatus: 'Status',
    colBudget: 'Budget',
  },
  eventsPage: {
    title: 'Event Timeline',
    eventsRecorded: 'events recorded',
    searchPlaceholder: 'Search by event type...',
    allEntities: 'All entities',
    sortToggleTitle: 'Toggle sort order',
    sortNewest: 'Newest',
    sortOldest: 'Oldest',
    refresh: 'Refresh',
    live: 'Live',
    loadingEvents: 'Loading events\u2026',
    retry: 'Retry',
    failedToLoad: 'Failed to load events',
    noEventsFound: 'No events found',
    tryAdjustingFilters: 'Try adjusting your filters',
    eventsWillAppear: 'Events will appear here once they are emitted',
    entity: 'Entity',
    entityId: 'Entity ID',
    severity: 'Severity',
  },
  aiCopilot: {
    title: 'AI Workforce',
    agentsActive: 'agents active',
    tasksCompleted: 'tasks completed',
    tabChat: 'chat',
    tabAgents: 'agents',
    tabActivity: 'activity',
    tabTools: 'tools',
    greeting: 'Welcome to the AI Workforce. I can connect you with specialized agents for executive, finance, procurement, project, sales, HR, and operations analysis.',
    sourcesLabel: 'Sources:',
    insightsLabel: 'Insights:',
    risksLabel: 'Risks:',
    actionsTakenLabel: 'Actions taken:',
    suggestionsLabel: 'Suggestions:',
    chatPlaceholder: 'Ask anything about your business...',
    unableToReach: 'Unable to reach the AI Copilot. Please try again.',
    suggestApproval: 'What needs my approval today?',
    suggestOverdue: 'Show me overdue invoices',
    suggestProjectHealth: 'Project health summary',
    suggestTopSuppliers: 'Top suppliers by spend',
    suggestBudgetReport: 'Budget utilization report',
    suggestRiskAssessment: 'Risk assessment for active projects',
    totalAgents: 'Total Agents',
    activeNow: 'Active Now',
    tasksCompletedStat: 'Tasks Completed',
    avgSuccessRate: 'Avg Success Rate',
    availableTools: 'Available Tools',
    tasksLabel: 'Tasks',
    successLabel: 'Success',
    toolsLabel: 'Tools',
    recentAiActivity: 'Recent AI Activity',
    aiToolRegistry: 'AI Tool Registry',
    aiToolRegistryDesc: 'Tools available to AI agents for executing business operations',
    toolAnalytics: 'Analytics Engine',
    toolAnalyticsDesc: 'Query and analyze business data',
    toolSearch: 'Global Search',
    toolSearchDesc: 'Search across all entities',
    toolReports: 'Report Generator',
    toolReportsDesc: 'Generate and run reports',
    toolNotifications: 'Notification Service',
    toolNotificationsDesc: 'Send notifications to users',
    toolWorkflow: 'Workflow Engine',
    toolWorkflowDesc: 'Trigger and manage workflows',
    toolDocuments: 'Document Intelligence',
    toolDocumentsDesc: 'OCR, classify, and extract data',
    toolLedger: 'Financial Ledger',
    toolLedgerDesc: 'Post and query financial entries',
    toolSuppliers: 'Supplier Management',
    toolSuppliersDesc: 'Search and compare suppliers',
    toolProjects: 'Project Management',
    toolProjectsDesc: 'Access project data and status',
    toolAutomation: 'Automation Engine',
    toolAutomationDesc: 'Execute automated business rules',
    toolIntegration: 'Integration Hub',
    toolIntegrationDesc: 'Connect to external systems',
    toolAudit: 'Audit Trail',
    toolAuditDesc: 'Track and query audit events',
  },
  entityPage: {
    back: 'Back',
    recordsLabel: 'Records',
    fieldsLabel: 'Fields',
    dataQuality: 'Data Quality',
    version: 'Version',
    tabOverview: 'Overview',
    tabData: 'Data',
    tabDocuments: 'Documents',
    tabTimeline: 'Timeline',
    tabAi: 'AI Insights',
    cancel: 'Cancel',
    newRecord: '+ New Record',
    save: 'Save',
    delete: 'Delete',
    entityDefinition: 'Entity Definition',
    code: 'Code',
    totalRecords: 'Total Records',
    editableFields: 'Editable Fields',
    computedFields: 'Computed Fields',
    fieldsSchema: 'Fields Schema',
    required: 'required',
    computed: 'computed',
    relatedEntities: 'Related Entities',
    records: 'records',
    newRecordTitle: 'New Record',
    versionColumn: 'Version',
    actionsColumn: 'Actions',
    noRecords: 'No records yet. Create one to get started.',
    recordDetails: 'Record Details',
    documentIntelligence: 'Document Intelligence',
    documentHint: 'Link documents to this entity for OCR, classification, and extraction',
    uploadDocument: 'Upload Document',
    entityTimeline: 'Entity Timeline',
    recordCreated: 'Record created',
    versionLabel: 'Version',
    noTimelineData: 'No timeline data yet',
    aiInsightsFor: 'AI Insights for',
    aiInsightsSubtitle: 'Ask questions about this entity\'s data',
    aiAskPlaceholder: 'Ask about',
    aiAskSuffix: 'records...',
    ask: 'Ask',
    showDuplicates: 'Show duplicates',
    dataQualityIssues: 'Data quality issues',
    trendsOverTime: 'Trends over time',
    anomalies: 'Anomalies',
    confirmDelete: 'Delete this record?',
    analysisComplete: 'Analysis complete.',
    analysisInitializing: 'Analysis feature is being initialized.',
    aiEngineConnecting: 'AI engine connecting...',
    createFailed: 'Create failed',
  },
  workspacePage: {
    askEos: 'Ask EOS',
    loadingDashboard: 'Loading dashboard...',
    unifiedDashboard: 'Unified Dashboard',
    dashboardSubtitle: 'Your tasks, approvals, KPIs, and alerts — all in one place',
    askPlaceholder: 'Ask about your project or finances...',
    asking: 'Asking...',
    aiConnectionError: 'Failed to connect to AI assistant',
    activeProjects: 'Active Projects',
    pendingApprovals: 'Pending Approvals',
    noPendingApprovals: 'No pending approvals',
    approveBtn: 'Approve',
    latestAlerts: 'Latest Alerts',
    noNewAlerts: 'No new alerts',
    myTasks: 'My Tasks',
    noActiveTasks: 'No active tasks',
  },
  builderPage: {
    eosBuilder: 'EOS Builder',
    subtitle: 'Business Model Compiler — describe your business objects, generate everything',
    objects: 'Objects',
    relations: 'Relations',
    workflows: 'Workflows',
    automations: 'Automations',
    rules: 'Rules',
    permissions: 'Permissions',
    wizardBasicInfo: 'Basic Info',
    wizardFields: 'Fields',
    wizardRelationships: 'Relationships',
    wizardRules: 'Rules',
    wizardWorkflow: 'Workflow',
    wizardPermissions: 'Permissions',
    wizardReview: 'Review',
    newObject: '+ New Object',
    edit: 'Edit',
    generate: 'Generate',
    del: 'Del',
    system: 'System',
    fields: 'fields',
    relationsCount: 'relations',
    rulesCount: 'rules',
    workflowsCount: 'workflows',
    noDescription: 'No description',
    noObjects: 'No objects yet',
    noObjectsHint: 'Click "+ New Object" to start building your business model',
    noRelationsDefined: 'No relations defined',
    noWorkflowsDefined: 'No workflows defined',
    trigger: 'Trigger',
    runs: 'Runs',
    statusLabel: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    noAutomationsDefined: 'No automations defined',
    when: 'WHEN',
    if: 'IF',
    then: 'THEN',
    noRulesDefined: 'No rules defined yet',
    noRulesHint: 'Create an object and add rules in the wizard',
    role: 'Role',
    create: 'Create',
    read: 'Read',
    update: 'Update',
    delete: 'Delete',
    approve: 'Approve',
    noObjectsToConfigure: 'No objects to configure',
    noObjectsHintPermissions: 'Create an object first to set up permissions',
    generateTitle: 'Generate:',
    generateDesc: 'The following artifacts will be generated from this business object definition:',
    databaseTable: 'Database table',
    apiEndpoints: 'API endpoints',
    uiForms: 'UI forms',
    permissionsGen: 'Permissions',
    workflowGen: 'Workflow',
    auditTrail: 'Audit trail',
    searchIndex: 'Search index',
    aiContext: 'AI context',
    generateAll: 'Generate All',
    createBusinessObject: 'Create Business Object',
    basicInformation: 'Basic Information',
    codeLabel: 'Code',
    codeHint: 'Unique identifier — used in API and database',
    nameLabel: 'Name',
    typeLabel: 'Type',
    entityType: 'Entity — Core business object',
    documentType: 'Document — File or record',
    transactionType: 'Transaction — Event or movement',
    referenceType: 'Reference — Lookup / config data',
    descriptionLabel: 'Description',
    descriptionPlaceholder: 'What does this object represent?',
    defineFields: 'Define Fields',
    addField: 'Add Field',
    required: 'Required',
    unique: 'Unique',
    addFieldBtn: '+ Add Field',
    defineRelationships: 'Define Relationships',
    addRelationship: 'Add Relationship',
    addRelationBtn: '+ Add Relation',
    defineRules: 'Define Rules',
    rulesPatternHint: 'Rules follow the pattern: WHEN event IF condition THEN action',
    addRule: 'Add Rule',
    defineWorkflow: 'Define Workflow',
    triggerType: 'Trigger Type',
    workflowStates: 'Workflow States',
    addState: 'Add state...',
    workflowHint: 'Press Enter to add a state. Typical flow: draft \u2192 pending \u2192 approved \u2192 rejected',
    visualFlow: 'Visual Flow',
    noStatesDefined: 'No states defined yet',
    setPermissions: 'Set Permissions',
    permissionsHint: 'Toggle access for each role across all actions',
    reviewAndCreate: 'Review & Create',
    unnamed: 'Unnamed',
    willGenerate: 'Will generate:',
    back: 'Back',
    next: 'Next',
    createObject: 'Create Object',
    cancel: 'Cancel',
    deleteConfirm: 'Delete this object? This cannot be undone.',
    loadingBuilder: 'Loading builder...',
  },
  settingsPage: {
    title: 'Settings',
    tabGeneral: 'General',
    tabAppearance: 'Appearance',
    tabNotifications: 'Notifications',
    tabSecurity: 'Security',
    tabIntegrations: 'Integrations',
    tabBilling: 'Billing',
    saved: 'Saved ✓',
    companyInformation: 'Company Information',
    companyName: 'Company Name',
    taxId: 'Tax ID',
    phone: 'Phone',
    email: 'Email',
    website: 'Website',
    address: 'Address',
    regionalSettings: 'Regional Settings',
    timezone: 'Timezone',
    dateFormat: 'Date Format',
    currency: 'Currency',
    language: 'Language',
    theme: 'Theme',
    leftToRight: 'Left-to-Right',
    rightToLeft: 'Right-to-Left',
    light: 'Light',
    dark: 'Dark',
    systemTheme: 'System',
    notificationChannels: 'Notification Channels',
    emailNotifications: 'Email Notifications',
    emailNotificationsDesc: 'Get notifications via email',
    pushNotifications: 'Push Notifications',
    pushNotificationsDesc: 'Browser push notifications',
    smsNotifications: 'SMS Notifications',
    smsNotificationsDesc: 'Receive critical alerts via SMS',
    notificationCategories: 'Notification Categories',
    weeklyReports: 'Weekly Reports',
    projectUpdates: 'Project Updates',
    approvalRequests: 'Approval Requests',
    budgetAlerts: 'Budget Alerts',
    paymentNotifications: 'Payment Notifications',
    changePassword: 'Change Password',
    currentPassword: 'Current Password',
    newPassword: 'New Password',
    confirmPassword: 'Confirm New Password',
    twoFactorAuth: 'Two-Factor Authentication',
    twoFAViaApp: '2FA via Authenticator App',
    useAuthenticatorApp: 'Use an authenticator app to generate one-time codes',
    enable: 'Enable',
    activeSessions: 'Active Sessions',
    currentSession: 'Current Session',
    lastActiveJustNow: 'Last active: Just now',
    active: 'Active',
    connectedServices: 'Connected Services',
    emailSMTP: 'Email (SMTP)',
    emailSMTPDesc: 'Configure email sending',
    smsGateway: 'SMS Gateway',
    smsGatewayDesc: 'Enable SMS notifications',
    paymentGateway: 'Payment Gateway',
    paymentGatewayDesc: 'Accept online payments',
    cloudStorage: 'Cloud Storage',
    cloudStorageDesc: 'Store documents in cloud',
    accountingSoftware: 'Accounting Software',
    accountingSoftwareDesc: 'Sync with accounting',
    connected: 'Connected',
    connect: 'Connect',
    currentPlan: 'Current Plan',
    professionalPlan: 'Professional Plan',
    planDescription: '50 users · All modules · AI features',
    usageThisMonth: 'Usage This Month',
    users: 'Users',
    aiQueries: 'AI Queries',
    storage: 'Storage',
    apiCalls: 'API Calls',
    paymentHistory: 'Payment History',
    paid: 'Paid',
    saveChanges: 'Save Changes',
    saving: 'Saving...',
    failedToSave: 'Failed to save',
    passwordsDoNotMatch: 'Passwords do not match',
    passwordComingSoon: 'Password change feature coming soon',
  },
  financialPage: {
    overview: 'Overview',
    accounts: 'Accounts',
    journal: 'Journal',
    ledger: 'Ledger',
    ar: 'AR',
    ap: 'AP',
    payments: 'Payments',
    bank: 'Bank',
    statements: 'Statements',
    ai: 'AI',
    subtitle: 'accounts',
    recentEntries: 'Recent Entries',
    recentInvoices: 'Recent Invoices',
    journalEntries: 'Journal Entries',
    noJournalEntries: 'No journal entries',
    noInvoices: 'No invoices',
    chartOfAccounts: 'Chart of Accounts',
    newAccount: '+ Account',
    code: 'Code',
    name: 'Name',
    type: 'Type',
    active: 'Active',
    asset: 'Asset',
    liability: 'Liability',
    equity: 'Equity',
    revenue: 'Revenue',
    expense: 'Expense',
    yes: 'Yes',
    no_: 'No',
    noAccounts: 'No accounts',
    account: 'Account',
    description: 'Description',
    reference: 'Reference',
    currency: 'Currency',
    status: 'Status',
    back: 'Back',
    doubleEntryLedger: 'Double-Entry Ledger',
    trialBalance: 'Trial Balance',
    fiscalPeriods: 'Fiscal Periods',
    chartOfAccountsTab: 'Chart of Accounts',
    date: 'Date',
    email: 'Email',
    journalEntriesTab: 'Journal Entries',
    newLedgerAccount: 'New Ledger Account',
    accountCode: 'Account Code',
    accountName: 'Account Name',
    normalBalance: 'Normal Balance',
    debit: 'Debit',
    credit: 'Credit',
    newJournalEntry: 'New Journal Entry',
    entryDate: 'Entry Date',
    referenceType: 'Reference Type',
    lines: 'Lines',
    addLine: '+ Add line',
    newFiscalPeriod: 'New Fiscal Period',
    periodName: 'Period Name',
    startDate: 'Start Date',
    endDate: 'End Date',
    post: 'Post',
    reverse: 'Reverse',
    total: 'Total',
    noLedgerAccounts: 'No ledger accounts',
    trialBalanceNotBalanced: 'Trial balance is not balanced!',
    loadingTrialBalance: 'Loading trial balance...',
    close: 'Close',
    noFiscalPeriods: 'No fiscal periods',
    accountsReceivable: 'Accounts Receivable',
    newCustomer: '+ Customer',
    newInvoice: '+ Invoice',
    customer: 'Customer',
    selectCustomer: 'Select customer',
    issueDate: 'Issue Date',
    dueDate: 'Due Date',
    paid: 'Paid',
    balanceDue: 'Balance Due',
    tax: 'Tax',
    number: 'Number',
    accountsPayable: 'Accounts Payable',
    newSupplier: '+ Supplier',
    newBill: '+ Bill',
    supplier: 'Supplier',
    selectSupplier: 'Select supplier',
    noBills: 'No bills',
    bankReconciliation: 'Bank & Reconciliation',
    newBankAccount: '+ Bank Account',
    accountNumber: 'Account Number',
    bankName: 'Bank Name',
    accountType: 'Type',
    checking: 'Checking',
    savings: 'Savings',
    creditAccount: 'Credit',
    cash: 'Cash',
    check: 'Check',
    glAccountId: 'GL Account ID',
    noBankAccounts: 'No bank accounts',
    reconciliations: 'Reconciliations',
    statementBalance: 'Statement Balance',
    bookBalance: 'Book Balance',
    difference: 'Difference',
    financialStatements: 'Financial Statements',
    profitAndLoss: 'Profit & Loss',
    totalRevenue: 'Total Revenue',
    totalExpenses: 'Total Expenses',
    netIncome: 'Net Income',
    balanceSheet: 'Balance Sheet',
    totalAssets: 'Total Assets',
    totalLiabilities: 'Total Liabilities',
    totalEquity: 'Total Equity',
    le: 'L + E',
    balanceNotBalanced: 'Balance sheet does not balance!',
    arAging: 'AR Aging',
    apAging: 'AP Aging',
    totalOutstanding: 'Total Outstanding',
    loading: 'Loading...',
    aiFinancialAnalyst: 'AI Financial Analyst',
    aiFinancialDesc: 'Analyze accounts, invoices, payments, and financial health',
    aiPlaceholder: "e.g., What's the AR aging? Which invoices are overdue?",
    ask: 'Ask',
    bankTransfer: 'Bank Transfer',
    select: 'Select',
    customerAR: 'Customer (AR)',
    supplierAP: 'Supplier (AP)',
  },
  projectsPage: {
    overview: 'Overview',
    financial: 'Financial',
    budget: 'Budget',
    contracts: 'Contracts',
    procurement: 'Procurement',
    documents: 'Documents',
    timeline: 'Timeline',
    risks: 'Risks',
    approvals: 'Approvals',
    aiInsights: 'AI Insights',
    budgetStat: 'Budget',
    spentStat: 'Spent',
    contractsStat: 'Contracts',
    claimsStat: 'Claims',
    procurementStat: 'Procurement',
    newProject: '+ New Project',
    cancel: 'Cancel',
    projectInformation: 'Project Information',
    code: 'Code',
    name: 'Name',
    client: 'Client',
    location: 'Location',
    manager: 'Manager',
    start: 'Start',
    end: 'End',
    progress: 'Progress',
    completion: 'Completion',
    budgetUsed: 'Budget Used',
    budgetUtilization: 'Budget Utilization',
    purchaseRequests: 'Purchase Requests',
    boqItems: 'BOQ Items',
    description: 'Description',
    noClient: 'No client',
    totalBudget: 'Total Budget',
    contractValue: 'Contract Value',
    claimsFiled: 'Claims Filed',
    prEstimated: 'PR Estimated',
    financialBreakdown: 'Financial Breakdown',
    noContractsLinked: 'No contracts linked',
    budgetAllocation: 'Budget Allocation',
    remaining: 'Remaining',
    boqSummary: 'BOQ Summary',
    noBoqItems: 'No BOQ items',
    noContractsLinkedToProject: 'No contracts linked to this project',
    noPurchaseRequests: 'No purchase requests for this project',
    documentIntelligence: 'Document Intelligence',
    documentHint: 'Upload contracts, drawings, RFIs, and submittals',
    uploadDocument: 'Upload Document',
    viewAll: 'View All',
    projectTimeline: 'Project Timeline',
    projectCreated: 'Project Created',
    contract: 'Contract',
    claim: 'Claim',
    pr: 'PR',
    budgetOverrun: 'Budget Overrun',
    claimsPending: 'Claims Pending',
    procurementBottleneck: 'Procurement Bottleneck',
    high: 'high',
    medium: 'medium',
    low: 'low',
    action: 'Action',
    pendingApprovals: 'Pending Approvals',
    approvalsHint: 'Approvals required for this project will appear here',
    aiProjectAnalyst: 'AI Project Analyst',
    aiProjectDesc: 'Ask questions about project health, budget, risks, and performance',
    aiPlaceholder: 'e.g., Why is budget utilization high?',
    ask: 'Ask',
    noProjects: 'No projects yet',
    save: 'Save',
    title: 'Title',
    status: 'Status',
    value: 'Value',
    prNumber: 'PR Number',
    estCost: 'Est. Cost',
  },
  contractsPage: {
    title: 'Contracts',
    subtitle: 'Manage contracts and agreements',
    newContract: 'New Contract',
    noContracts: 'No contracts yet',
    backToContracts: 'Contracts',
    contractsCount: 'contracts',
    totalValueLabel: 'total value',
    value: 'Value',
    type: 'Type',
    project: 'Project',
    status: 'Status',
    overview: 'Overview',
    financial: 'Financial',
    timeline: 'Timeline',
    documents: 'Documents',
    risks: 'Risks',
    aiInsights: 'AI Insights',
    contractDetails: 'Contract Details',
    number: 'Number',
    titleField: 'Title',
    counterpartyField: 'Counterparty',
    contractValue: 'Contract Value',
    signed: 'Signed',
    completion: 'Completion',
    contractHealth: 'Contract Health',
    statusLabel: 'Status',
    contractInGoodStanding: 'Contract is in good standing',
    daysActive: 'Days Active',
    daysToCompletion: 'Days to Completion',
    financialSummary: 'Financial Summary',
    invoiced: 'Invoiced',
    remaining: 'Remaining',
    contractTimeline: 'Contract Timeline',
    contractCreated: 'Contract Created',
    contractSigned: 'Contract Signed',
    expectedCompletion: 'Expected Completion',
    notYet: 'Not yet',
    contractDocuments: 'Contract Documents',
    documentsSubtitle: 'Upload signed contracts, amendments, and related documents',
    uploadDocument: 'Upload Document',
    contractExpiry: 'Contract Expiry',
    valueExposure: 'Value Exposure',
    expiresLabel: 'Expires',
    noExpirySet: 'No expiry set',
    monitorContractStatus: 'Monitor contract status',
    reviewFinancialExposure: 'Review financial exposure',
    contractValueLabel: 'contract value',
    aiContractAnalyst: 'AI Contract Analyst',
    aiContractDesc: 'Analyze contract terms, risks, and financial implications',
    aiPlaceholder: 'e.g., What are the key risks in this contract?',
    ask: 'Ask',
    analysisComplete: 'Analysis complete.',
    analysisInitializing: 'Analysis feature is being initialized.',
    aiConnecting: 'AI engine connecting...',
    riskAssessment: 'Risk assessment',
    financialAnalysis: 'Financial analysis',
    timelineReview: 'Timeline review',
    complianceCheck: 'Compliance check',
    contractNumber: 'Contract Number',
  },
  procurementPage: {
    tabOverview: 'Overview',
    tabRequests: 'Requests',
    tabSuppliers: 'Suppliers',
    tabOrders: 'Orders',
    tabAnalysis: 'Analysis',
    tabAi: 'AI',
    newRequest: '+ New Request',
    cancel: 'Cancel',
    save: 'Save',
    totalRequests: 'Total Requests',
    draft: 'Draft',
    approved: 'Approved',
    ordered: 'Ordered',
    priorityDistribution: 'Priority Distribution',
    recentRequests: 'Recent Requests',
    noProcurementRequests: 'No procurement requests',
    requisition: 'Requisition',
    title: 'Title',
    priority: 'Priority',
    status: 'Status',
    details: 'Details',
    estValue: 'Est. Value',
    noRequests: 'No requests',
    newProcurementRequest: 'New Procurement Request',
    requisitionNumber: 'Requisition #',
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    urgent: 'Urgent',
    supplierManagement: 'Supplier Management',
    supplierManagementDesc: 'Manage your supplier relationships and vendor performance',
    purchaseOrders: 'Purchase Orders',
    purchaseOrdersDesc: 'Track purchase orders from creation to delivery',
    totalValue: 'Total Value',
    avgPerRequest: 'Avg. per Request',
    pending: 'Pending',
    aiProcurementAdvisor: 'AI Procurement Advisor',
    aiProcurementDesc: 'Optimize procurement decisions, supplier selection, and cost analysis',
    aiPlaceholder: 'e.g., What items need urgent procurement?',
    ask: 'Ask',
    analysisComplete: 'Analysis complete.',
    analysisInitializing: 'Analysis feature is being initialized.',
    aiConnecting: 'AI engine connecting...',
  },
  notificationsPage: {
    title: 'Notifications',
    subtitle: 'System notifications and alerts',
    errorLoading: 'Failed to load notifications',
    errorMarkRead: 'Failed to mark as read',
    errorMarkAllRead: 'Failed to mark all as read',
    justNow: 'Just now',
    minutesAgo: 'm ago',
    hoursAgo: 'h ago',
    daysAgo: 'd ago',
    unreadLabel: 'unread',
    markAllRead: 'Mark All Read',
    statsTotal: 'Total',
    statsUnread: 'Unread',
    statsToday: 'Today',
    statsThisWeek: 'This Week',
    filterAll: 'All',
    filterUnread: 'Unread',
    filterApprovals: 'Approvals',
    filterSystem: 'System',
    filterAlerts: 'Alerts',
    noNotifications: 'No notifications',
    allCaughtUp: "You're all caught up!",
    relatedEntity: 'Related Entity',
    viewRelated: 'View Related',
    markAsRead: 'Mark as Read',
    dismiss: 'Dismiss',
  },
  auditPage: {
    title: 'Audit Log',
    actionLabel: 'Action',
    filterByAction: 'Filter by action...',
    resourceType: 'Resource Type',
    filterByResource: 'Filter by resource...',
    clear: 'Clear',
    action: 'Action',
    resourceId: 'Resource ID',
    actor: 'Actor',
    timestamp: 'Timestamp',
    details: 'Details',
    view: 'View',
  },
  documentsPage: {
    loading: 'Loading documents...',
    title: 'Document Intelligence',
    documentsCount: 'documents',
    total: 'Total',
    processed: 'Processed',
    processing: 'Processing',
    failed: 'Failed',
    categories: 'Categories',
    searchPlaceholder: 'Search documents...',
    allCategories: 'All Categories',
    invoice: 'Invoice',
    receipt: 'Receipt',
    contract: 'Contract',
    purchaseOrder: 'Purchase Order',
    goodsReceived: 'Goods Received',
    report: 'Report',
    other: 'Other',
    search: 'Search',
    file: 'File',
    category: 'Category',
    status: 'Status',
    classification: 'Classification',
    size: 'Size',
    actions: 'Actions',
    extract: 'Extract',
    classify: 'Classify',
    po: 'PO',
    noDocumentsFound: 'No documents found',
    categoryLabel: 'Category:',
    statusLabel: 'Status:',
    typeLabel: 'Type:',
    mimeLabel: 'MIME:',
    extractedData: 'Extracted Data:',
    ocrText: 'OCR Text:',
  },
  boqPage: {
    title: 'Bill of Quantities',
    subtitle: 'Manage BOQ items and versions',
    createBoq: 'Create BOQ',
    editBoq: 'Edit BOQ',
    contract: 'Contract',
    contractRequired: 'Contract *',
    selectContract: 'Select Contract',
    version: 'Version',
    status: 'Status',
    draft: 'Draft',
    submitted: 'Submitted',
    approved: 'Approved',
    confirm: 'Confirm',
    areYouSure: 'Are you sure?',
    failedToLoad: 'Failed to load BOQs',
    failedToSave: 'Failed to save',
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
    home: 'الرئيسية',
    businessObjects: 'كائنات الأعمال',
    businessGraph: 'الرسم البياني للأعمال',
    workflows: 'سير العمل',
    rules: 'القواعد',
    events: 'الأحداث',
    analytics: 'التحليلات',
    aiCopilot: 'المساعد الذكي',
    documents: 'المستندات',
    integrations: 'التكاملات',
    globalization: 'العولمة',
    builder: 'المنشئ',
    developerSdk: 'SDK للمطورين',
    marketplace: 'السوق',
    workspace: 'مساحة العمل',
    overview: 'نظرة عامة',
    tenants: 'العملاء',
    rolesPermissions: 'الأدوار والصلاحيات',
    plans: 'الخطط',
    billing: 'الفوترة',
    featureFlags: 'أعلام المميزات',
    aiControlCenter: 'مركز التحكم في الذكاء الاصطناعي',
    automation: 'الأتمتة',
    applications: 'التطبيقات',
    apiManagement: 'إدارة API',
    securityCenter: 'مركز الأمان',
    auditLogs: 'سجلات التدقيق',
    systemHealth: 'صحة النظام',
    backupRecovery: 'النسخ الاحتياطي والاستعادة',
    support: 'الدعم',
    search: 'بحث',
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
    systemHealth: 'صحة النظام',
    allSystems: 'جميع الأنظمة',
    revenueGrowth: 'نمو الإيرادات',
    tenantGrowth: 'نمو العملاء',
    userGrowth: 'نمو المستخدمين',
    aiUsage: 'استخدام الذكاء الاصطناعي',
    operational: 'تشغيل',
    warning: 'تحذير',
    critical: 'حرج',
    newTenantRegistered: 'عميل جديد مسجل',
    paymentProcessed: 'تمت معالجة الدفع',
    aiModelUpdated: 'تم تحديث نموذج الذكاء الاصطناعي',
    userSuspended: 'تم تعليق المستخدم',
    backupCompleted: 'اكتمل النسخ الاحتياطي',
    minutesAgo: 'دقائق مضت',
    hoursAgo: 'ساعات مضت',
    daysAgo: 'أيام مضت',
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
    titleField: 'العنوان',
    counterparty: 'الطرف المقابل',
    totalAmount: 'المبلغ الإجمالي',
    status: 'الحالة',
    draft: 'مسودة',
    pendingApproval: 'بانتظار الاعتماد',
    active: 'نشط',
    completed: 'مكتمل',
    terminated: 'منهي',
    signedDate: 'تاريخ التوقيع',
    completionDate: 'تاريخ الإنجاز',
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
    date: 'التاريخ',
    period: 'الفترة',
    pending: 'قيد المراجعة',
    draft: 'مسودة',
    submitted: 'مقدّمة',
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
    requisitionNumber: 'رقم طلب الشراء',
    project: 'المشروع',
    priority: 'الأولوية',
    low: 'منخفضة',
    medium: 'متوسطة',
    high: 'عالية',
    urgent: 'عاجلة',
    draft: 'مسودة',
    pendingApproval: 'بانتظار الاعتماد',
    approved: 'معتمدة',
    ordered: 'تم الطلب',
    received: 'تم الاستلام',
    invoiced: 'تمت الفاتورة',
    paid: 'مدفوعة',
    cancelled: 'ملغاة',
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
    skip: 'تخطي',
  },
  landing: {
    features: 'المميزات',
    pricing: 'التسعير',
    docs: 'التوثيق',
    signIn: 'تسجيل الدخول',
    heroTitle1: 'شركتك,',
    heroTitle2: 'نظام واحد',
    heroSubtitle: '2TO EOS هو نظام تشغيل أعمال بالذكاء الاصطناعي يحول نموذج أعمالك وبياناته وقواعده وسير عمله إلى منصة ذكية واحدة.',
    startTrial: 'ابدأ التجربة المجانية',
    watchDemo: 'شاهد العرض',
    problemTitle: 'شركتك تعمل على 12 أداة مختلفة',
    solutionTitle: 'منصة واحدة لإدارة كل شيء',
    solutionSubtitle: '2TO EOS يستبدل حزمة برمجياتك بمنصة ذكية واحدة بالكامل.',
    ctaTitle: 'جاهز لتحويل أعمالك؟',
    ctaSubtitle: 'انضم لمئات الشركات التي تستخدم 2TO EOS.',
    getStarted: 'ابدأ الآن',
    learnMore: 'اعرف المزيد',
    tools: ['المحاسبة', 'Excel', 'واتساب', 'إدارة العملاء', 'الموارد البشرية', 'المخزون', 'البريد', 'البنوك', 'المستندات', 'المشاريع', 'ذكاء الأعمال', 'البوابات'],
    footerRights: '© 2026 2TO. جميع الحقوق محفوظة.',
  },
  login: {
    backToHome: 'العودة للرئيسية',
    title: '2TO EOS',
    subtitle: 'نظام تشغيل الأعمال',
    emailLabel: 'البريد الإلكتروني',
    passwordLabel: 'كلمة المرور',
    signIn: 'تسجيل الدخول',
    signingIn: 'جاري تسجيل الدخول...',
    noAccount: 'ليس لديك حساب؟',
    createWorkspace: 'إنشاء مساحة عمل جديدة',
  },
  onboard: {
    welcomeTitle: 'مرحباً بك في EOS',
    welcomeSubtitle: 'نظام تشغيل أعمالك بالذكاء الاصطناعي. دعنا نجهز مساحة عملك في خطوات قليلة.',
    getStarted: 'ابدأ الآن',
    companyName: 'اسم الشركة',
    companyNamePlaceholder: 'مثال: شركة المايا',
    industry: 'الصناعة',
    industryPlaceholder: 'مثال: التكنولوجيا، البناء...',
    inviteTeam: 'دعوة فريق العمل',
    invitePlaceholder: 'أدخل عناوين البريد الإلكتروني مفصولة بفواصل',
    completeTitle: 'أنت جاهز!',
    completeSubtitle: 'مساحة عملك جاهزة. ابدأ في استكشاف نظام ERP الجديد.',
    goToDashboard: 'الذهاب للوحة التحكم',
  },
  sidebar: {
    platform: 'المنصة',
    erp: 'ERP',
    administration: 'الإدارة',
    master: 'الرئيسي',
  },
  adminSidebar: {
    eosControlCenter: 'لوحة تحكم EOS',
    systemOwner: 'مالك النظام',
    superAdmin: 'مدير النظام',
    featureFlags: 'أعلام المميزات',
    securityCenter: 'مركز الأمان',
    auditLogs: 'سجلات التدقيق',
    systemHealth: 'صحة النظام',
    systemSettings: 'إعدادات النظام',
    globalSearch: 'بحث شامل',
    notificationsCenter: 'الإشعارات',
    backupRecovery: 'النسخ الاحتياطي والاستعادة',
    apiManagement: 'إدارة API',
    automationCenter: 'الأتمتة',
    supportCenter: 'الدعم',
    applications: 'التطبيقات',
    integrationsHub: 'التكاملات',
    master: 'الرئيسي',
    overview: 'نظرة عامة',
    groupOrganization: 'المؤسسة',
    groupCommerce: 'التجارة',
    groupPlatform: 'المنصة',
    groupAi: 'الذكاء الاصطناعي',
    groupAutomation: 'الأتمتة',
    groupSecurity: 'الأمان',
    groupSystem: 'النظام',
    groupSupport: 'الدعم',
    groupMaster: 'الرئيسي',
    tenants: 'العملاء',
    users: 'المستخدمون',
    rolesPermissions: 'الأدوار والصلاحيات',
    plans: 'الخطط',
    subscriptions: 'الاشتراكات',
    billing: 'الفوترة',
    transactions: 'المعاملات',
    aiControlCenter: 'مركز التحكم في الذكاء الاصطناعي',
    aiModels: 'نماذج الذكاء الاصطناعي',
    aiWorkforce: 'القوى العاملة الذكية',
    aiUsage: 'استخدام الذكاء الاصطناعي',
    workflows: 'سير العمل',
    automations: 'الأتمتة',
    jobs: 'المهام',
    sessions: 'الجلسات',
    monitoring: 'المراقبة',
    tickets: 'التذاكر',
    supportPage: 'الدعم',
  },
  adminHeader: {
    quickActions: 'إجراءات سريعة',
    newTenant: 'عميل جديد',
    newUser: 'مستخدم جديد',
    newPlan: 'خطة جديدة',
    newRole: 'دور جديد',
    newApiKey: 'مفتاح API جديد',
    newAiAgent: 'وكيل ذكاء اصطناعي جديد',
    disableSystem: 'تعطيل النظام',
    notifications: 'الإشعارات',
    searchPlaceholder: 'بحث عن العملاء، المستخدمين، الفواتير، مفاتيح API...',
    confirmDangerousAction: 'تأكيد الإجراء الخطير',
    confirmDangerousMessage: 'هذا الإجراء قد يسبب اضطراباً في النظام بالكامل. هل أنت متأكد؟',
  },
  master: {
    title: 'مركز التحكم الرئيسي',
    subtitle: 'لوحة تحكم شاملة للمنصة',
    overview: {
      title: 'نظرة عامة',
      totalTenants: 'إجمالي العملاء',
      activeTenants: 'العملاء النشطون',
      suspendedTenants: 'العملاء المعلّقون',
      totalUsers: 'إجمالي المستخدمين',
      activeUsers: 'المستخدمين النشطين',
      newTenants: 'عملاء جدد',
      mrr: 'الإيرادات الشهرية',
      arr: 'الإيرادات السنوية',
      revenue: 'الإيرادات',
      outstandingPayments: 'المستحقات المعلقة',
      aiUsage: 'استخدام الذكاء الاصطناعي',
      apiUsage: 'استخدام API',
      automationRuns: 'تنفيذ الأتمتة',
      storageUsage: 'استخدام التخزين',
      analyticsTab: 'التحليلات',
    },
    health: {
      title: 'حالة النظام',
      apiStatus: 'حالة API',
      databaseStatus: 'حالة قاعدة البيانات',
      aiServicesStatus: 'خدمات الذكاء الاصطناعي',
      backgroundJobs: 'الوظائف الخلفية',
      queueStatus: 'حالة الطابور',
      storageStatus: 'حالة التخزين',
      emailService: 'خدمة البريد',
      paymentGateway: 'بوابة الدفع',
      externalIntegrations: 'التكاملات الخارجية',
      aiServices: 'خدمات الذكاء الاصطناعي',
      storage: 'التخزين',
      integrations: 'التكاملات',
      cpu: 'المعالج',
      ram: 'الذاكرة',
      disk: 'استخدام القرص',
      database: 'زمن استجابة قاعدة البيانات',
      apiLatency: 'زمن استجابة API',
      requestsPerSec: 'الطلبات / ثانية',
      errorRate: 'معدل الأخطاء',
      queue: 'طول الطابور',
      operational: 'تشغيل',
      warning: 'تحذير',
      critical: 'حرج',
      offline: 'غير متصل',
    },
    tenants: {
      title: 'إدارة العملاء',
      searchPlaceholder: 'بحث العملاء...',
      companyName: 'اسم الشركة',
      owner: 'المالك',
      industry: 'الصناعة',
      country: 'البلد',
      plan: 'الخطة',
      status: 'الحالة',
      users: 'المستخدمين',
      storage: 'التخزين',
      aiUsage: 'استخدام الذكاء الاصطناعي',
      createdAt: 'تاريخ الإنشاء',
      lastActivity: 'آخر نشاط',
      actions: 'الإجراءات',
      view: 'عرض',
      edit: 'تعديل',
      suspend: 'تعليق',
      activate: 'تفعيل',
      delete: 'حذف',
      impersonate: 'انتحال الهوية',
      changePlan: 'تغيير الخطة',
    },
    users: {
      title: 'إدارة المستخدمين',
      searchPlaceholder: 'بحث المستخدمين...',
      user: 'المستخدم',
      email: 'البريد الإلكتروني',
      tenant: 'العميل',
      role: 'الدور',
      status: 'الحالة',
      mfa: 'MFA',
      lastLogin: 'آخر تسجيل دخول',
      created: 'تم الإنشاء',
      sessions: 'الجلسات',
      riskStatus: 'حالة الخطر',
      actions: 'الإجراءات',
      view: 'عرض',
      edit: 'تعديل',
      suspend: 'تعليق',
      activate: 'تفعيل',
      resetPassword: 'إعادة تعيين كلمة المرور',
      forceLogout: 'إجبار الخروج',
      resetMFA: 'إعادة تعيين MFA',
      delete: 'حذف',
    },
    roles: {
      title: 'الأدوار والصلاحيات',
      systemRoles: 'الأدوار النظامية',
      tenantRoles: 'أدوار العملاء',
      customRoles: 'الأدوار المخصصة',
      permissions: 'الصلاحيات',
      permissionGroups: 'مجموعات الصلاحيات',
    },
    plans: {
      title: 'خطط الاشتراك',
      pricing: 'التسعير',
      features: 'المميزات',
      limits: 'الحدود',
      trialPeriod: 'فترة التجربة',
      usageLimits: 'حدود الاستخدام',
      aiLimits: 'حدود الذكاء الاصطناعي',
      storageLimits: 'حدود التخزين',
      userLimits: 'حدود المستخدمين',
      apiLimits: 'حدود API',
      actions: {
        createPlan: 'إنشاء خطة',
        editPlan: 'تعديل الخطة',
        duplicatePlan: 'نسخ الخطة',
        archivePlan: 'أرشفة الخطة',
        changePricing: 'تغيير التسعير',
        configureFeatures: 'تكوين المميزات',
      },
    },
    billing: {
      title: 'مركز الفوترة',
      revenue: 'الإيرادات',
      mrr: 'الإيرادات الشهرية',
      arr: 'الإيرادات السنوية',
      invoices: 'الفواتير',
      payments: 'المدفوعات',
      failedPayments: 'المدفوعات الفاشلة',
      refunds: 'المبالغ المستردة',
      taxes: 'الضرائب',
      transactions: 'المعاملات',
    },
    featureFlags: {
      title: 'أعلام المميزات',
      erp: 'ERP',
      aiWorkforce: 'قوة العمل الذكية',
      automation: 'الأتمتة',
      analytics: 'التحليلات',
      industryOS: 'Industry OS',
      advancedReports: 'التقارير المتقدمة',
      api: 'API',
      integrations: 'التكاملات',
      global: 'عالمي',
      byPlan: 'حسب الخطة',
      byTenant: 'حسب العميل',
      byUser: 'حسب المستخدم',
      enable: 'تفعيل',
      disable: 'تعطيل',
      rolloutPercent: 'نسبة الإطلاق',
    },
    aiControl: {
      title: 'مركز الذكاء الاصطناعي',
      models: 'النماذج',
      providers: 'المزودين',
      modelUsage: 'استخدام النموذج',
      tokenUsage: 'استخدام الرموز',
      cost: 'التكلفة',
      requests: 'الطلبات',
      latency: 'تأخير',
      errors: 'الأخطاء',
      aiAgents: 'وكلاء الذكاء الاصطناعي',
      aiWorkforce: 'قوة العمل الذكية',
      promptManagement: 'إدارة التعليمات',
      aiPolicies: 'سياسات الذكاء الاصطناعي',
      modelRouting: 'توجيه النماذج',
      modelManagement: {
        provider: 'المزود',
        modelName: 'اسم النموذج',
        status: 'الحالة',
        cost: 'التكلفة',
        contextWindow: 'نافذة السياق',
        rateLimits: 'حدود المعدل',
        default: 'افتراضي',
        backup: 'احتياطي',
        enable: 'تفعيل',
        disable: 'تعطيل',
        configure: 'تكوين',
        setDefault: 'تعيين كافتراضي',
        setFallback: 'تعيين كاحتياطي',
      },
    },
    automation: {
      title: 'مركز الأتمتة',
      workflows: 'سير العمل',
      automations: 'الأتمتة',
      jobs: 'المهام',
      automationName: 'اسم الأتمتة',
      tenant: 'العميل',
      trigger: 'المُحفّز',
      status: 'الحالة',
      executions: 'التنفيذات',
      successRate: 'معدل النجاح',
      errors: 'الأخطاء',
      lastRun: 'آخر تشغيل',
      actions: {
        enable: 'تفعيل',
        disable: 'تعطيل',
        edit: 'تعديل',
        duplicate: 'نسخ',
        test: 'اختبار',
        viewLogs: 'عرض السجلات',
      },
    },
    integrations: {
      title: 'مركز التكاملات',
      payment: 'الدفع',
      email: 'البريد الإلكتروني',
      sms: 'رسالة نصية',
      whatsapp: 'واتساب',
      accounting: 'المحاسبة',
      crm: 'إدارة العملاء',
      storage: 'التخزين',
      aiProviders: 'مزودي الذكاء الاصطناعي',
      webhooks: 'Webhooks',
      apis: 'APIs',
      integration: 'التكامل',
      provider: 'المزود',
      connectedTenants: 'العملاء المتصلين',
      errors: 'الأخطاء',
      lastSync: 'آخر مزامنة',
    },
    api: {
      title: 'إدارة API',
      apiKeys: 'مفاتيح API',
      apiClients: 'عملاء API',
      requests: 'الطلبات',
      rateLimits: 'حدود المعدل',
      webhooks: 'Webhooks',
      apiErrors: 'أخطاء API',
      apiUsage: 'استخدام API',
      createApiKey: 'إنشاء مفتاح API',
      revoke: 'إلغاء',
      rotate: 'تدوير',
      setPermissions: 'تعيين الصلاحيات',
      setRateLimits: 'تعيين حدود المعدل',
    },
    security: {
      title: 'مركز الأمان',
      loginAttempts: 'محاولات تسجيل الدخول',
      failedLogins: 'تسجيلات الدخول الفاشلة',
      suspiciousActivity: 'النشاط المشبوه',
      activeSessions: 'الجلسات النشطة',
      mfaStatus: 'حالة MFA',
      securityEvents: 'الأحداث الأمنية',
      ipActivity: 'نشاط IP',
      apiSecurity: 'أمان API',
      accessViolations: 'انتهاكات الوصول',
      forceLogout: 'إجبار الخروج',
      blockIP: 'حظر IP',
      revokeToken: 'إلغاء الرمز',
      disableAccount: 'تعطيل الحساب',
      requireMFA: 'إلزام MFA',
    },
    auditLogs: {
      title: 'سجلات التدقيق',
      user: 'المستخدم',
      tenant: 'العميل',
      action: 'الإجراء',
      resource: 'المورد',
      timestamp: 'الطابع الزمني',
      ip: 'IP',
      device: 'الجهاز',
      result: 'النتيجة',
      filters: {
        date: 'التاريخ',
        user: 'المستخدم',
        tenant: 'العميل',
        action: 'الإجراء',
        resource: 'المورد',
        ip: 'IP',
        success: 'نجاح',
        failure: 'فشل',
      },
    },
    systemHealth: {
      title: 'صحة النظام',
      cpu: 'المعالج',
      ram: 'الذاكرة',
      disk: 'القرص',
      database: 'قاعدة البيانات',
      apiLatency: 'تأخير API',
      requestsPerSec: 'طلبات/ثانية',
      errorRate: 'معدل الأخطاء',
      queue: 'الطابور',
      backgroundJobs: 'الوظائف الخلفية',
      activeIncidents: 'الحوادث النشطة',
      warnings: 'التحذيرات',
      resolvedIncidents: 'الحوادث المحلولة',
    },
    backups: {
      title: 'النسخ الاحتياطي والاستعادة',
      databaseBackups: 'نسخ قاعدة البيانات الاحتياطية',
      fileBackups: 'نسخ الملفات الاحتياطية',
      backupSchedule: 'جدول النسخ الاحتياطي',
      backupStatus: 'حالة النسخ الاحتياطي',
      restorePoints: 'نقاط الاستعادة',
      createBackup: 'إنشاء نسخة احتياطية',
      restore: 'استعادة',
      download: 'تحميل',
      delete: 'حذف',
      configureSchedule: 'تكوين الجدول',
    },
    notifications: {
      title: 'مركز الإشعارات',
      global: 'إشعار عام',
      tenantSpecific: 'إشعار مخصص للعميل',
      userSpecific: 'إشعار مخصص للمستخدم',
      announcement: 'إعلان',
      maintenance: 'صيانة',
      security: 'أمان',
      billing: 'فوترة',
      systemAlert: 'تنبيه النظام',
    },
    support: {
      title: 'مركز الدعم',
      supportTickets: 'تذاكر الدعم',
      tenantIssues: 'قضايا العملاء',
      userIssues: 'قضايا المستخدمين',
      systemIssues: 'قضايا النظام',
      ticket: 'التذكرة',
      priority: 'الأولوية',
      status: 'الحالة',
      assignedTo: 'المُعين إليه',
      created: 'تم الإنشاء',
      updated: 'تم التحديث',
    },
    quickActions: {
      create: 'إنشاء',
      newTenant: 'عميل جديد',
      newUser: 'مستخدم جديد',
      newPlan: 'خطة جديدة',
      newRole: 'دور جديد',
      newFeature: 'مميزات جديدة',
      newNotification: 'إشعار جديد',
      newApiKey: 'مفتاح API جديد',
      newAiAgent: 'وكيل ذكاء اصطناعي جديد',
    },
    settings: {
      general: 'عام',
      email: 'البريد الإلكتروني',
      notifications: 'الإشعارات',
      security: 'الأمان',
      system: 'النظام',
      ai: 'الذكاء الاصطناعي',
    },
    common: {
      loading: 'جاري التحميل...',
      search: 'بحث...',
      noData: 'لا توجد بيانات',
      total: 'المجموع',
      actions: 'الإجراءات',
      view: 'عرض',
      edit: 'تعديل',
      delete: 'حذف',
      suspend: 'تعطيل',
      activate: 'تفعيل',
      enable: 'تمكين',
      disable: 'تعطيل',
      confirm: 'تأكيد',
      cancel: 'إلغاء',
      save: 'حفظ',
      close: 'إغلاق',
      create: 'إنشاء',
      new: 'جديد',
      filter: 'تصفية',
      all: 'الكل',
      success: 'نجاح',
      failed: 'فشل',
      warning: 'تحذير',
      active: 'نشط',
      inactive: 'غير نشط',
      back: 'رجوع',
      next: 'التالي',
      export: 'تصدير',
      import: 'استيراد',
      download: 'تحميل',
      upload: 'رفع',
      refresh: 'تحديث',
      retry: 'إعادة المحاولة',
      createdAt: 'تم الإنشاء',
      updatedAt: 'تم التحديث',
      lastActive: 'آخر نشاط',
    },
  },
  applications: {
    title: 'التطبيقات',
    subtitle: 'إدارة تطبيقات ومنصات المنصة',
    tenants: 'عميل',
  },
  globalSearch: {
    title: 'بحث شامل',
    subtitle: 'بحث في جميع موارد النظام',
    searchPlaceholder: 'بحث عن العملاء، المستخدمين، الفواتير، مفاتيح API...',
  },
  integrationsHub: {
    title: 'مركز التكاملات',
    subtitle: 'إدارة جميع اتصالات النظام الخارجية',
    lastSync: 'آخر مزامنة',
    configure: 'تكوين',
    realtime: 'فوري',
    tenants: 'عميل',
  },
  systemHealth: {
    title: 'صحة النظام والمراقبة',
    subtitle: 'مراقبة البنية التحتية في الوقت الفعلي',
    systemIncidents: 'حوادث النظام',
    backgroundJobs: 'الوظائف الخلفية',
    elevatedDisk: 'ارتفاع استخدام القرص على العقدة 3',
    queueBacklog: 'اكتشاف تراكم في الطابور',
    scheduledMaintenance: 'صيانة مجدولة',
    dailyBackup: 'نسخ احتياطي يومي',
    aiModelTraining: 'تدريب نموذج الذكاء الاصطناعي',
    emailDispatch: 'إرسال البريد',
    reportGeneration: 'إنشاء التقارير',
  },
  systemSettings: {
    title: 'إعدادات النظام',
    subtitle: 'تكوين شامل للمنصة',
    saveChanges: 'حفظ التغييرات',
    generalTab: 'عام',
    emailTab: 'البريد الإلكتروني',
    notificationsTab: 'الإشعارات',
    securityTab: 'الأمان',
    systemTab: 'النظام',
    aiTab: 'الذكاء الاصطناعي',
    platformName: 'اسم المنصة',
    defaultLanguage: 'اللغة الافتراضية',
    timezone: 'المنطقة الزمنية',
    defaultCurrency: 'العملة الافتراضية',
    smtpHost: 'خادم SMTP',
    senderEmail: 'بريد المرسل',
    templates: 'القوالب',
    emailNotifications: 'إشعارات البريد الإلكتروني',
    pushNotifications: 'الإشعارات الفورية',
    smsAlerts: 'تنبيهات SMS',
    sessionTimeout: 'مهلة الجلسة',
    passwordMinLength: 'الحد الأدنى لكلمة المرور',
    mfaRequired: 'إلزام MFA',
    maintenanceMode: 'وضع الصيانة',
    debugMode: 'وضع التصحيح',
    cacheDuration: 'مدة التخزين المؤقت',
    defaultModel: 'النموذج الافتراضي',
    fallbackModel: 'النموذج الاحتياطي',
    tokenLimit: 'حد الرموز',
  },
  securityCenter: {
    title: 'مركز الأمان',
    subtitle: 'مراقبة الأحداث الأمنية والجلسات النشطة والتهديدات',
    recentEvents: 'الأحداث الأمنية الأخيرة',
    type: 'النوع',
    user: 'المستخدم',
    ip: 'IP',
    result: 'النتيجة',
    time: 'الوقت',
    device: 'الجهاز',
  },
  notificationsCenter: {
    title: 'مركز الإشعارات',
    subtitle: 'إرسال إشعارات عامة أو مخصصة للعميل أو المستخدم',
    sendNotification: 'إرسال إشعار',
    notificationTitle: 'عنوان الإشعار',
    message: 'الرسالة',
    scope: 'النطاق',
    category: 'الفئة',
    send: 'إرسال',
  },
  backupRecovery: {
    title: 'النسخ الاحتياطي والاستعادة',
    subtitle: 'نسخ قاعدة البيانات الاحتياطية ونسخ الملفات ونقاط الاستعادة',
    lastBackup: 'آخر نسخة احتياطية',
    totalBackups: 'إجمالي النسخ الاحتياطية',
    createBackup: 'إنشاء نسخة احتياطية',
    restore: 'استعادة',
    id: 'المعرف',
    type: 'النوع',
    size: 'الحجم',
    status: 'الحالة',
    date: 'التاريخ',
    duration: 'المدة',
  },
  apiManagement: {
    title: 'إدارة API',
    subtitle: 'إدارة مفاتيح API والعملاء وحدود المعدل',
    totalRequests: 'إجمالي الطلبات',
    activeKeys: 'المفاتيح النشطة',
    createApiKey: 'إنشاء مفتاح API',
    key: 'المفتاح',
    name: 'الاسم',
    tenant: 'العميل',
    requests: 'الطلبات',
    rateLimit: 'حد المعدل',
    rotate: 'تدوير',
    revoke: 'إلغاء',
  },
  automationCenter: {
    title: 'مركز الأتمتة',
    subtitle: 'إدارة سير العمل والأتمتة',
    newAutomation: 'أتمتة جديدة',
    name: 'الاسم',
    tenant: 'العميل',
    trigger: 'المُحفّز',
    executions: 'التنفيذات',
    successRate: 'معدل النجاح',
    lastRun: 'آخر تشغيل',
    running: 'قيد التشغيل',
    paused: 'متوقف مؤقتاً',
    failed: 'فشل',
  },
  supportCenter: {
    title: 'مركز الدعم',
    subtitle: 'إدارة تذاكر الدعم والمشاكل',
    newTicket: 'تذكرة جديدة',
    ticket: 'التذكرة',
    tenant: 'العميل',
    priority: 'الأولوية',
    assigned: 'المُعين',
    created: 'تاريخ الإنشاء',
    open: 'مفتوحة',
    inProgress: 'قيد المعالجة',
    resolved: 'محلولة',
  },
  executiveDashboard: {
    searchPlaceholder: 'ابحث عن المشاريع أو الموردين أو المستندات أو اسأل EOS عن أي شيء...',
    workspace: 'مساحة العمل',
    whatNeedsAttention: 'ما الذي يحتاج انتباهك اليوم',
    askEos: 'اسأل EOS',
    askEosSubtitle: 'اسأل عن أي شيء في أعمالك — حلل، نفّذ، أتمت',
    askEosPlaceholder: 'مثال: أظهر الفواتير المتأخرة، ما هو هامش المشروع، أظهر الموردين الذين يتجاوزون الميزانية...',
    analyzing: 'جارٍ التحليل...',
    analysisComplete: 'اكتمل التحليل.',
    aiFallbackResponse: 'يمكنني المساعدة في المشاريع والمالية والمشتريات والموافقات وتحليل الموردين. جرّب السؤال عن تجاوزات الميزانية أو الفواتير المتأخرة.',
    suggestApproval: 'ما الذي يحتاج موافقت؟',
    suggestOverdue: 'أظهر الفواتير المتأخرة',
    suggestArAging: 'ملخص تقادم الحسابات المدينة',
    suggestProjectHealth: 'ملخص صحة المشاريع',
    suggestTopSuppliers: 'أعلى الموردين من حيث الإنفاق',
    suggestBudgetReport: 'تقرير استخدام الميزانية',
    statRecords: 'السجلات',
    statApprovals: 'الموافقات',
    statWorkflows: 'سير العمل',
    statArOutstanding: 'المستحقات المدينة',
    statApOutstanding: 'المستحقات الدائنة',
    statDocuments: 'المستندات',
    tabOverview: 'نظرة عامة',
    tabAttention: 'انتباه',
    tabFinancial: 'المالية',
    tabRisks: 'المخاطر',
    tabActivity: 'النشاط',
    quickNavigation: 'التنقل السريع',
    businessObjects: 'الكائنات التجارية',
    noDataYet: 'لا توجد بيانات بعد.',
    recentEvents: 'الأحداث الأخيرة',
    noEventsYet: 'لا توجد أحداث بعد.',
    pendingApprovals: 'الموافقات المعلقة',
    approve: 'موافقة',
    reject: 'رفض',
    allClearNoApprovals: 'كل شيء على ما يرام! لا توجد موافقات معلقة.',
    overdueInvoices: 'الفواتير المتأخرة',
    due: 'تاريخ الاستحقاق',
    noOverdueInvoices: 'لا توجد فواتير متأخرة',
    overdueBills: 'الفواتير المستحقة المتأخرة',
    noOverdueBills: 'لا توجد فواتير مستحقة متأخرة',
    activeWorkflows: 'سير العمل النشطة',
    state: 'الحالة',
    noActiveWorkflows: 'لا توجد سير عمل نشطة',
    arAging: 'تقادم الحسابات المدينة',
    apAging: 'تقادم الحسابات الدائنة',
    current: 'جاري',
    totalAr: 'إجمالي المدينة',
    totalAp: 'إجمالي الدائنة',
    noData: 'لا توجد بيانات',
    recentInvoices: 'الفواتير الأخيرة',
    noInvoices: 'لا توجد فواتير',
    dueAmount: 'مستحق',
    recentBills: 'الفواتير المستحقة الأخيرة',
    noBills: 'لا توجد فواتير مستحقة',
    noDetectedRisks: 'لا توجد مخاطر مكتشفة',
    allSystemsNormal: 'جميع الأنظمة تعمل بشكل طبيعي',
    ruleActivity: 'نشاط القواعد',
    noRuleFirings: 'لا توجد إطلاقات قواعد بعد.',
    documentIntelligence: 'الذكاء المستنداتي',
    docTotal: 'الإجمالي',
    docProcessed: 'تمت المعالجة',
    docProcessing: 'جارٍ المعالجة',
    docFailed: 'فشل',
    activeProjects: 'المشاريع النشطة',
    noClient: 'لا يوجد عميل',
    budgetSuffix: 'الميزانية',
    actionLabel: 'الإجراء',
  },
  businessObjectsExplorer: {
    title: 'الكائنات التجارية',
    publishedEntities: 'كيانات منشورة',
    searchPlaceholder: 'ابحث عن الكيانات...',
    fields: 'حقول',
    noObjectsFound: 'لم يتم العثور على كائنات تجارية.',
    publishHint: 'انشر الكيانات عبر واجهة البيانات الوصفية لرؤيتها هنا.',
  },
  businessGraph: {
    title: 'الخريطة التجارية',
    subtitle: 'استكشف كيف تتصل كائناتك التجارية — كل كيان يروي قصة',
    entityType: 'نوع الكيان',
    record: 'سجل',
    depth: 'العمق',
    loading: 'جارٍ التحميل...',
    noRecords: 'لا توجد سجلات',
    refreshGraph: 'تحديث الخريطة',
    nodes: 'العقد',
    edges: 'الروابط',
    entityTypes: 'أنواع الكيانات',
    entryNode: 'عقدة الدخول',
    entity: 'الكيان',
    titleLabel: 'العنوان',
    recordId: 'رقم السجل',
    selectToVisualize: 'اختر كياناً وسجلاً لتصور الخريطة التجارية.',
    nodeDetails: 'تفاصيل العقدة',
    connections: 'الاتصالات',
    data: 'البيانات',
    entityLegend: 'دليل الكيانات',
  },
  workflowsPage: {
    title: 'سير العمل',
    subtitle: 'إدارة نماذج سير العمل والموافقات والقوالب',
    tabInstances: 'النماذج',
    tabApprovals: 'الموافقات',
    tabTemplates: 'القوالب',
    tabHistory: 'السجل',
    startWorkflow: 'بدء سير عمل',
    refresh: 'تحديث',
    noInstances: 'لا توجد نماذج سير عمل',
    noInstancesHint: 'ستظهر سير العمل هنا بمجرد بدئها.',
    startNewWorkflow: 'بدء سير عمل جديد',
    template: 'القالب',
    selectTemplate: 'اختر قالباً...',
    referenceType: 'نوع المرجع',
    referenceTypePlaceholder: 'مثال: مصروف، أمر شراء',
    referenceId: 'رقم المرجع',
    referenceIdPlaceholder: 'مثال: exp_12345',
    cancel: 'إلغاء',
    start: 'بدء',
    history: 'السجل',
    currentState: 'الحالة الحالية',
    instanceId: 'رقم النموذج',
    tenant: 'المستأجر',
    referenceTypeLabel: 'نوع المرجع',
    referenceIdLabel: 'رقم المرجع',
    availableTransitions: 'الانتقالات المتاحة',
    noTransitions: 'لا توجد انتقالات متاحة لهذه الحالة.',
    approval: 'موافقة',
    allCaughtUp: 'لقد حققت بكل شيء',
    noPendingApprovals: 'لا توجد موافقات معلقة في الوقت الحالي.',
    colAction: 'الإجراء',
    colTransition: 'الانتقال',
    colInstance: 'النموذج',
    colStatus: 'الحالة',
    colActions: 'الإجراءات',
    approve: 'موافقة',
    reject: 'رفض',
    delegate: 'تفويض',
    noTemplates: 'لا توجد قوالب',
    noTemplatesHint: 'ستظهر قوالب سير العمل هنا.',
    states: 'الحالات',
    transitions: 'الانتقالات',
    stateDiagram: 'مخطط الحالات',
    selectInstanceHint: 'اختر نموذجاً من تبويب النماذج لعرض سجله.',
    goToInstances: 'الذهاب إلى النماذج',
    workflowHistory: 'سجل سير العمل',
    cancelWorkflow: 'إلغاء سير العمل',
    noHistoryEntries: 'لا توجد سجلات بعد.',
    timeline: 'الجدول الزمني',
  },
  rulesPage: {
    title: 'القواعد',
    subtitle: 'قواعد الأتمتة التي تستجيب لأحداث المنصة',
    cancel: 'إلغاء',
    newRule: 'قاعدة جديدة',
    createRule: 'إنشاء قاعدة',
    name: 'الاسم',
    namePlaceholder: 'مثال: تحديد المشتريات عالية القيمة',
    eventType: 'نوع الحدث',
    eventTypePlaceholder: 'purchase_request.created',
    priority: 'الأولوية',
    enabled: 'مفعّل',
    conditions: 'الشروط',
    addCondition: '+ إضافة شرط',
    fieldPlaceholder: 'الحقل (مثال: payload.amount)',
    valuePlaceholder: 'القيمة',
    actions: 'الإجراءات',
    remove: 'إزالة',
    titleLabel: 'العنوان',
    alertTitlePlaceholder: 'عنوان التنبيه',
    messageLabel: 'الرسالة',
    notificationMessagePlaceholder: 'رسالة الإشعار',
    roleOptional: 'الدور (اختياري)',
    rolePlaceholder: 'مثال: manager',
    entityTypeOptional: 'نوع الكيان (اختياري)',
    entityTypePlaceholder: 'مثال: purchase_request',
    messageOptional: 'الرسالة (اختياري)',
    auditLogPlaceholder: 'رسالة سجل التدقيق',
    creating: 'جارٍ الإنشاء...',
    createRuleButton: 'إنشاء قاعدة',
    noRulesYet: 'لا توجد قواعد بعد',
    noRulesHint: 'ستظهر القواعد هنا بمجرد إنشائها.',
    noActions: 'لا إجراءات',
    created: 'أنشئ',
    ruleExecutions: 'تنفيذات القواعد',
    recentExecutionHistory: 'سجل تنفيذ القواعد الأخيرة',
    noExecutions: 'لا توجد تنفيذات مسجلة بعد.',
    colRule: 'القاعدة',
    colMatched: 'مطابق',
    colDetail: 'التفاصيل',
    colExecutedAt: 'نُفّذ في',
    matched: 'مطابق',
    noMatch: 'غير مطابق',
    failedToCreateRule: 'فشل إنشاء القاعدة',
  },
  analyticsPage: {
    title: 'التحليلات',
    subtitle: 'رؤى تنفيذية مع إمكانية التعمق',
    tabExecutive: 'تنفيذي',
    tabFinancial: 'المالية',
    tabOperational: 'تشغيلي',
    tabProjects: 'المشاريع',
    businessRecords: 'السجلات التجارية',
    activeProjects: 'المشاريع النشطة',
    totalBudget: 'إجمالي الميزانية',
    documentProcessing: 'معالجة المستندات',
    entityDistribution: 'توزيع الكيانات',
    systemHealth: 'صحة النظام',
    dataCompleteness: 'اكتمال البيانات',
    activeWorkflows: 'سير العمل النشطة',
    ruleCoverage: 'تغطية القواعد',
    rulesLabel: 'قواعد',
    totalProjects: 'إجمالي المشاريع',
    acrossAllProjects: 'عبر جميع المشاريع',
    processedLabel: 'تمت المعالجة',
    detailsLabel: 'التفاصيل',
    totalRevenue: 'إجمالي الإيرادات',
    totalExpenses: 'إجمالي المصروفات',
    netProfit: 'صافي الربح',
    cashPosition: 'الوضع النقدي',
    financialSummary: 'الملخص المالي',
    accountsReceivable: 'الحسابات المدينة',
    accountsPayable: 'الحسابات الدائنة',
    workingCapital: 'رأس المال العامل',
    budgetVsActual: 'الميزانية مقابل الفعلي',
    documentIntelligence: 'استخراج المستندات',
    budgetLabel: 'الميزانية',
    procurement: 'المشتريات',
    contracts: 'العقود',
    documents: 'المستندات',
    eventsToday: 'أحداث اليوم',
    pendingPrs: 'طلبات شراء معلقة',
    active: 'نشط',
    total: 'الإجمالي',
    recentActivity: 'النشاط الأخير',
    noRecentEvents: 'لا توجد أحداث حديثة',
    totalProjectsLabel: 'إجمالي المشاريع',
    activeLabel: 'نشط',
    planning: 'التخطيط',
    completed: 'مكتمل',
    colCode: 'الكود',
    colName: 'الاسم',
    colStatus: 'الحالة',
    colBudget: 'الميزانية',
  },
  eventsPage: {
    title: 'الجدول الزمني للأحداث',
    eventsRecorded: 'أحداث مسجلة',
    searchPlaceholder: 'ابحث حسب نوع الحدث...',
    allEntities: 'جميع الكيانات',
    sortToggleTitle: 'تبديل ترتيب الفرز',
    sortNewest: 'الأحدث',
    sortOldest: 'الأقدم',
    refresh: 'تحديث',
    live: 'مباشر',
    loadingEvents: 'جارٍ تحميل الأحداث...',
    retry: 'إعادة المحاولة',
    failedToLoad: 'فشل تحميل الأحداث',
    noEventsFound: 'لم يتم العثور على أحداث',
    tryAdjustingFilters: 'حاول تعديل مرشحاتك',
    eventsWillAppear: 'ستظهر الأحداث هنا بمجرد إصدارها',
    entity: 'الكيان',
    entityId: 'رقم الكيان',
    severity: 'الخطورة',
  },
  aiCopilot: {
    title: 'قوة العمل بالذكاء الاصطناعي',
    agentsActive: 'وكلاء نشطين',
    tasksCompleted: 'مهام مكتملة',
    tabChat: 'محادثة',
    tabAgents: 'الوكلاء',
    tabActivity: 'النشاط',
    tabTools: 'الأدوات',
    greeting: 'مرحباً بك في قوة العمل بالذكاء الاصطناعي. يمكنني توصلك بوكلاء متخصصين للتحليل التنفيذي والمالي والمشتريات والمبيعات وموارد البشرية والعمليات.',
    sourcesLabel: 'المصادر:',
    insightsLabel: 'رؤى:',
    risksLabel: 'المخاطر:',
    actionsTakenLabel: 'الإجراءات المتخذة:',
    suggestionsLabel: 'اقتراحات:',
    chatPlaceholder: 'اسأل عن أي شيء في أعمالك...',
    unableToReach: 'تعذر الوصول إلى المساعد الذكي. يرجى المحاولة مرة أخرى.',
    suggestApproval: 'ما الذي يحتاج موافقت اليوم؟',
    suggestOverdue: 'أرني الفواتير المتأخرة',
    suggestProjectHealth: 'ملخص صحة المشاريع',
    suggestTopSuppliers: 'أعلى الموردين من حيث الإنفاق',
    suggestBudgetReport: 'تقرير استخدام الميزانية',
    suggestRiskAssessment: 'تقييم المخاطر للمشاريع النشطة',
    totalAgents: 'إجمالي الوكلاء',
    activeNow: 'نشط الآن',
    tasksCompletedStat: 'المهام المكتملة',
    avgSuccessRate: 'متوسط نسبة النجاح',
    availableTools: 'الأدوات المتاحة',
    tasksLabel: 'المهام',
    successLabel: 'النجاح',
    toolsLabel: 'الأدوات',
    recentAiActivity: 'نشاط الذكاء الاصطناعي الأخير',
    aiToolRegistry: 'سجل أدوات الذكاء الاصطناعي',
    aiToolRegistryDesc: 'الأدوات المتاحة لوكلاء الذكاء الاصطناعي لتنفيذ العمليات التجارية',
    toolAnalytics: 'محرك التحليلات',
    toolAnalyticsDesc: 'استعلام وتحليل البيانات التجارية',
    toolSearch: 'بحث عام',
    toolSearchDesc: 'البحث عبر جميع الكيانات',
    toolReports: 'مولّد التقارير',
    toolReportsDesc: 'إنشاء وتشغيل التقارير',
    toolNotifications: 'خدمة الإشعارات',
    toolNotificationsDesc: 'إرسال الإشعارات للمستخدمين',
    toolWorkflow: 'محرك سير العمل',
    toolWorkflowDesc: 'تشغيل وإدارة سير العمل',
    toolDocuments: 'الذكاء المستنداتي',
    toolDocumentsDesc: 'تمييز بصري، تصنيف واستخراج البيانات',
    toolLedger: 'الدفتر المالي',
    toolLedgerDesc: 'تسجيل واستعلام القيود المالية',
    toolSuppliers: 'إدارة الموردين',
    toolSuppliersDesc: 'بحث ومقارنة الموردين',
    toolProjects: 'إدارة المشاريع',
    toolProjectsDesc: 'الوصول لبيانات المشاريع وحالتها',
    toolAutomation: 'محرك الأتمتة',
    toolAutomationDesc: 'تنفيذ قواعد الأعمال الآلية',
    toolIntegration: 'مركز التكامل',
    toolIntegrationDesc: 'الاتصال بالأنظمة الخارجية',
    toolAudit: 'سجل التدقيق',
    toolAuditDesc: 'تتبع واستعلام أحداث التدقيق',
  },
  entityPage: {
    back: 'رجوع',
    recordsLabel: 'السجلات',
    fieldsLabel: 'الحقول',
    dataQuality: 'جودة البيانات',
    version: 'الإصدار',
    tabOverview: 'نظرة عامة',
    tabData: 'البيانات',
    tabDocuments: 'المستندات',
    tabTimeline: 'الجدول الزمني',
    tabAi: 'رؤى الذكاء الاصطناعي',
    cancel: 'إلغاء',
    newRecord: '+ سجل جديد',
    save: 'حفظ',
    delete: 'حذف',
    entityDefinition: 'تعريف الكيان',
    code: 'الكود',
    totalRecords: 'إجمالي السجلات',
    editableFields: 'الحقول القابلة للتعديل',
    computedFields: 'الحقول المحسوبة',
    fieldsSchema: 'مخطط الحقول',
    required: 'مطلوب',
    computed: 'محسوب',
    relatedEntities: 'الكيانات ذات الصلة',
    records: 'سجلات',
    newRecordTitle: 'سجل جديد',
    versionColumn: 'الإصدار',
    actionsColumn: 'الإجراءات',
    noRecords: 'لا توجد سجلات بعد. أنشئ سجلاً للبدء.',
    recordDetails: 'تفاصيل السجل',
    documentIntelligence: 'الذكاء المستنداتي',
    documentHint: 'اربط المستندات بهذا الكيان للتمييز البصري والتصنيف والاستخراج',
    uploadDocument: 'رفع مستند',
    entityTimeline: 'الجدول الزمني للكيان',
    recordCreated: 'تم إنشاء السجل',
    versionLabel: 'الإصدار',
    noTimelineData: 'لا توجد بيانات زمنية بعد',
    aiInsightsFor: 'رؤى الذكاء الاصطناعي لـ',
    aiInsightsSubtitle: 'اسأل عن بيانات هذا الكيان',
    aiAskPlaceholder: 'اسأل عن',
    aiAskSuffix: 'سجلات...',
    ask: 'اسأل',
    showDuplicates: 'إظهار المكررات',
    dataQualityIssues: 'مشاكل جودة البيانات',
    trendsOverTime: 'الاتجاهات عبر الوقت',
    anomalies: 'الشذوذات',
    confirmDelete: 'هل تريد حذف هذا السجل؟',
    analysisComplete: 'اكتمل التحليل.',
    analysisInitializing: 'ميزة التحليل قيد التهيئة.',
    aiEngineConnecting: 'محرك الذكاء الاصطناعي يتصل...',
    createFailed: 'فشل الإنشاء',
  },
  workspacePage: {
    askEos: 'اسأل EOS',
    loadingDashboard: 'جاري تحميل لوحة التحكم...',
    unifiedDashboard: 'لوحة التحكم الموحدة',
    dashboardSubtitle: 'مهامك، الموافقات، مؤشرات الأداء، والتنبيهات — كلها في مكان واحد',
    askPlaceholder: 'اسأل عن مشروعك أو ماليّاتك...',
    asking: 'جارٍ السؤال...',
    aiConnectionError: 'تعذّر الاتصال بالمساعد الذكي',
    activeProjects: 'مشاريع نشطة',
    pendingApprovals: 'الموافقات المعلقة',
    noPendingApprovals: 'لا توجد موافقات معلقة',
    approveBtn: 'موافقة',
    latestAlerts: 'أحدث التنبيهات',
    noNewAlerts: 'لا توجد تنبيهات جديدة',
    myTasks: 'مهامي',
    noActiveTasks: 'لا توجد مهام نشطة',
  },
  builderPage: {
    eosBuilder: 'منشئ EOS',
    subtitle: 'محرر النموذج التجاري — صِف كائنات عملك، أنشئ كل شيء',
    objects: 'الكائنات',
    relations: 'العلاقات',
    workflows: 'سير العمل',
    automations: 'الأتمتة',
    rules: 'القواعد',
    permissions: 'الصلاحيات',
    wizardBasicInfo: 'المعلومات الأساسية',
    wizardFields: 'الحقول',
    wizardRelationships: 'العلاقات',
    wizardRules: 'القواعد',
    wizardWorkflow: 'سير العمل',
    wizardPermissions: 'الصلاحيات',
    wizardReview: 'المراجعة',
    newObject: '+ كائن جديد',
    edit: 'تعديل',
    generate: 'توليد',
    del: 'حذف',
    system: 'النظام',
    fields: 'حقول',
    relationsCount: 'علاقات',
    rulesCount: 'قواعد',
    workflowsCount: 'سير عمل',
    noDescription: 'لا يوجد وصف',
    noObjects: 'لا توجد كائنات بعد',
    noObjectsHint: 'انقر "+ كائن جديد" لبدء بناء نموذج عملك',
    noRelationsDefined: 'لم يتم تعريف علاقات',
    noWorkflowsDefined: 'لم يتم تعريف سير عمل',
    trigger: 'المُشغّل',
    runs: 'التشغيلات',
    statusLabel: 'الحالة',
    active: 'نشط',
    inactive: 'غير نشط',
    noAutomationsDefined: 'لم يتم تعريف أتمتة',
    when: 'عندما',
    if: 'إذا',
    then: 'فإن',
    noRulesDefined: 'لم يتم تعريف قواعد بعد',
    noRulesHint: 'أنشئ كائناً وأضف قواعد في معالج الإنشاء',
    role: 'الدور',
    create: 'إنشاء',
    read: 'قراءة',
    update: 'تحديث',
    delete: 'حذف',
    approve: 'موافقة',
    noObjectsToConfigure: 'لا توجد كائنات لإعدادها',
    noObjectsHintPermissions: 'أنشئ كائناً أولاً لإعداد الصلاحيات',
    generateTitle: 'توليد:',
    generateDesc: 'سيتم توليد المنتجات التالية من تعريف الكائن التجاري هذا:',
    databaseTable: 'جدول قاعدة البيانات',
    apiEndpoints: 'نقاط نهاية API',
    uiForms: 'نماذج واجهة المستخدم',
    permissionsGen: 'الصلاحيات',
    workflowGen: 'سير العمل',
    auditTrail: 'سجل التدقيق',
    searchIndex: 'فهرس البحث',
    aiContext: 'سياق الذكاء الاصطناعي',
    generateAll: 'توليد الكل',
    createBusinessObject: 'إنشاء كائن تجاري',
    basicInformation: 'المعلومات الأساسية',
    codeLabel: 'الكود',
    codeHint: 'معرف فريد — مستخدم في API وقاعدة البيانات',
    nameLabel: 'الاسم',
    typeLabel: 'النوع',
    entityType: 'كيان — كائن تجاري أساسي',
    documentType: 'مستند — ملف أو سجل',
    transactionType: 'معاملة — حدث أو حركة',
    referenceType: 'مرجع — بيانات بحث / تكوين',
    descriptionLabel: 'الوصف',
    descriptionPlaceholder: 'ماذا يمثل هذا الكائن؟',
    defineFields: 'تعريف الحقول',
    addField: 'إضافة حقل',
    required: 'مطلوب',
    unique: 'فريد',
    addFieldBtn: '+ إضافة حقل',
    defineRelationships: 'تعريف العلاقات',
    addRelationship: 'إضافة علاقة',
    addRelationBtn: '+ إضافة علاقة',
    defineRules: 'تعريف القواعد',
    rulesPatternHint: 'القواعد تتبع النمط: عندما حدث إذا شرط فإن إجراء',
    addRule: 'إضافة قاعدة',
    defineWorkflow: 'تعريف سير العمل',
    triggerType: 'نوع المُشغّل',
    workflowStates: 'حالات سير العمل',
    addState: 'إضافة حالة...',
    workflowHint: 'اضغط Enter لإضافة حالة. التدفق النموذجي: مسودة \u2192 معلق \u2192 معتمد \u2192 مرفوض',
    visualFlow: 'التدفق المرئي',
    noStatesDefined: 'لم يتم تعريف حالات بعد',
    setPermissions: 'تعيين الصلاحيات',
    permissionsHint: 'تبديل الوصول لكل دور عبر جميع الإجراءات',
    reviewAndCreate: 'مراجعة وإنشاء',
    unnamed: 'بدون اسم',
    willGenerate: 'سيتم توليد:',
    back: 'رجوع',
    next: 'التالي',
    createObject: 'إنشاء الكائن',
    cancel: 'إلغاء',
    deleteConfirm: 'حذف هذا الكائن؟ لا يمكن التراجع عن هذا الإجراء.',
    loadingBuilder: 'جارٍ تحميل المنشئ...',
  },
  settingsPage: {
    title: 'الإعدادات',
    tabGeneral: 'عام',
    tabAppearance: 'المظهر',
    tabNotifications: 'الإشعارات',
    tabSecurity: 'الأمان',
    tabIntegrations: 'التكاملات',
    tabBilling: 'الفوترة',
    saved: 'تم الحفظ ✓',
    companyInformation: 'معلومات الشركة',
    companyName: 'اسم الشركة',
    taxId: 'الرقم الضريبي',
    phone: 'الهاتف',
    email: 'البريد الإلكتروني',
    website: 'الموقع الإلكتروني',
    address: 'العنوان',
    regionalSettings: 'الإعدادات الإقليمية',
    timezone: 'المنطقة الزمنية',
    dateFormat: 'تنسيق التاريخ',
    currency: 'العملة',
    language: 'اللغة',
    theme: 'المظهر',
    leftToRight: 'من اليسار إلى اليمين',
    rightToLeft: 'من اليمين إلى اليسار',
    light: 'فاتح',
    dark: 'داكن',
    systemTheme: 'النظام',
    notificationChannels: 'قنوات الإشعارات',
    emailNotifications: 'إشعارات البريد الإلكتروني',
    emailNotificationsDesc: 'الحصول على الإشعارات عبر البريد الإلكتروني',
    pushNotifications: 'الإشعارات الفورية',
    pushNotificationsDesc: 'إشعارات المتصفح الفورية',
    smsNotifications: 'إشعارات الرسائل النصية',
    smsNotificationsDesc: 'تلقّي التنبيهات الحرجة عبر الرسائل النصية',
    notificationCategories: 'فئات الإشعارات',
    weeklyReports: 'التقارير الأسبوعية',
    projectUpdates: 'تحديثات المشاريع',
    approvalRequests: 'طلبات الاعتماد',
    budgetAlerts: 'تنبيهات الميزانية',
    paymentNotifications: 'إشعارات الدفع',
    changePassword: 'تغيير كلمة المرور',
    currentPassword: 'كلمة المرور الحالية',
    newPassword: 'كلمة المرور الجديدة',
    confirmPassword: 'تأكيد كلمة المرور الجديدة',
    twoFactorAuth: 'المصادقة الثنائية',
    twoFAViaApp: 'المصادقة الثنائية عبر تطبيق المصادقة',
    useAuthenticatorApp: 'استخدم تطبيق المصادقة لإنشاء رموز لمرة واحدة',
    enable: 'تفعيل',
    activeSessions: 'الجلسات النشطة',
    currentSession: 'الجلسة الحالية',
    lastActiveJustNow: 'آخر نشاط: للتو',
    active: 'نشط',
    connectedServices: 'الخدمات المتصلة',
    emailSMTP: 'البريد الإلكتروني (SMTP)',
    emailSMTPDesc: 'تكوين إرسال البريد الإلكتروني',
    smsGateway: 'بوابة الرسائل النصية',
    smsGatewayDesc: 'تفعيل إشعارات الرسائل النصية',
    paymentGateway: 'بوابة الدفع',
    paymentGatewayDesc: 'قبول المدفوعات عبر الإنترنت',
    cloudStorage: 'التخزين السحابي',
    cloudStorageDesc: 'تخزين المستندات في السحابة',
    accountingSoftware: 'البرامج المحاسبية',
    accountingSoftwareDesc: 'المزامنة مع المحاسبة',
    connected: 'متصل',
    connect: 'اتصال',
    currentPlan: 'الخطة الحالية',
    professionalPlan: 'الخطة الاحترافية',
    planDescription: '50 مستخدم · جميع الوحدات · ميزات الذكاء الاصطناعي',
    usageThisMonth: 'الاستخدام هذا الشهر',
    users: 'المستخدمون',
    aiQueries: 'استعلامات الذكاء الاصطناعي',
    storage: 'التخزين',
    apiCalls: 'استدعاءات API',
    paymentHistory: 'سجل الدفعات',
    paid: 'مدفوع',
    saveChanges: 'حفظ التغييرات',
    saving: 'جارٍ الحفظ...',
    failedToSave: 'فشل الحفظ',
    passwordsDoNotMatch: 'كلمتا المرور غير متطابقتين',
    passwordComingSoon: 'ميزة تغيير كلمة المرور قادمة قريباً',
  },
  financialPage: {
    overview: 'نظرة عامة',
    accounts: 'الحسابات',
    journal: 'القيود',
    ledger: 'الدفتر',
    ar: 'المدينون',
    ap: 'الدائنون',
    payments: 'المدفوعات',
    bank: 'البنك',
    statements: 'القوائم المالية',
    ai: 'الذكاء الاصطناعي',
    subtitle: 'حسابات',
    recentEntries: 'القيود الأخيرة',
    recentInvoices: 'الفواتير الأخيرة',
    journalEntries: 'القيود اليومية',
    noJournalEntries: 'لا توجد قيود يومية',
    noInvoices: 'لا توجد فواتير',
    chartOfAccounts: 'دليل الحسابات',
    newAccount: '+ حساب',
    code: 'الكود',
    name: 'الاسم',
    type: 'النوع',
    active: 'نشط',
    asset: 'أصول',
    liability: 'خصوم',
    equity: 'حقوق ملكية',
    revenue: 'إيرادات',
    expense: 'مصروفات',
    yes: 'نعم',
    no_: 'لا',
    noAccounts: 'لا توجد حسابات',
    account: 'الحساب',
    description: 'الوصف',
    reference: 'المرجع',
    currency: 'العملة',
    status: 'الحالة',
    back: 'رجوع',
    doubleEntryLedger: 'دفتر الأستاذ المزدوج',
    trialBalance: 'ميزان المراجعة',
    fiscalPeriods: 'الفترات المالية',
    chartOfAccountsTab: 'دليل الحسابات',
    date: 'التاريخ',
    email: 'البريد الإلكتروني',
    journalEntriesTab: 'القيود اليومية',
    newLedgerAccount: 'حساب دفتر أستاذ جديد',
    accountCode: 'رمز الحساب',
    accountName: 'اسم الحساب',
    normalBalance: 'الرصيد الطبيعي',
    debit: 'مدين',
    credit: 'دائن',
    newJournalEntry: 'قيد يومي جديد',
    entryDate: 'تاريخ القيد',
    referenceType: 'نوع المرجع',
    lines: 'البنود',
    addLine: '+ إضافة بند',
    newFiscalPeriod: 'فترة مالية جديدة',
    periodName: 'اسم الفترة',
    startDate: 'تاريخ البداية',
    endDate: 'تاريخ النهاية',
    post: 'ترحيل',
    reverse: 'عكس',
    total: 'الإجمالي',
    noLedgerAccounts: 'لا توجد حسابات دفتر الأستاذ',
    trialBalanceNotBalanced: 'ميزان المراجعة غير متوازن!',
    loadingTrialBalance: 'جارٍ تحميل ميزان المراجعة...',
    close: 'إغلاق',
    noFiscalPeriods: 'لا توجد فترات مالية',
    accountsReceivable: 'الحسابات المدينة',
    newCustomer: '+ عميل',
    newInvoice: '+ فاتورة',
    customer: 'العميل',
    selectCustomer: 'اختر عميلاً',
    issueDate: 'تاريخ الإصدار',
    dueDate: 'تاريخ الاستحقاق',
    paid: 'مدفوع',
    balanceDue: 'المبلغ المستحق',
    tax: 'الضريبة',
    number: 'الرقم',
    accountsPayable: 'الحسابات الدائنة',
    newSupplier: '+ مورد',
    newBill: '+ فاتورة مشتريات',
    supplier: 'المورد',
    selectSupplier: 'اختر مورداً',
    noBills: 'لا توجد فواتير مشتريات',
    bankReconciliation: 'البنك والتسوية',
    newBankAccount: '+ حساب بنكي',
    accountNumber: 'رقم الحساب',
    bankName: 'اسم البنك',
    accountType: 'النوع',
    checking: 'جاري',
    savings: 'ادخار',
    creditAccount: 'ائتمان',
    cash: 'نقدي',
    check: 'شيك',
    glAccountId: 'رقم حساب الدفتر العام',
    noBankAccounts: 'لا توجد حسابات بنكية',
    reconciliations: 'التسويات',
    statementBalance: 'رصيد الكشف',
    bookBalance: 'رصيد الدفتر',
    difference: 'الفرق',
    financialStatements: 'القوائم المالية',
    profitAndLoss: 'قائمة الأرباح والخسائر',
    totalRevenue: 'إجمالي الإيرادات',
    totalExpenses: 'إجمالي المصروفات',
    netIncome: 'صافي الدخل',
    balanceSheet: 'الميزانية العمومية',
    totalAssets: 'إجمالي الأصول',
    totalLiabilities: 'إجمالي الخصوم',
    totalEquity: 'إجمالي حقوق الملكية',
    le: 'خ + م',
    balanceNotBalanced: 'الميزانية العمومية غير متوازنة!',
    arAging: 'أعمار الحسابات المدينة',
    apAging: 'أعمار الحسابات الدائنة',
    totalOutstanding: 'إجمالي المستحقات',
    loading: 'جارٍ التحميل...',
    aiFinancialAnalyst: 'المحلل المالي بالذكاء الاصطناعي',
    aiFinancialDesc: 'تحليل الحسابات والفواتير والمدفوعات والصحة المالية',
    aiPlaceholder: 'مثال: ما هي أعمار الحسابات المدينة؟ أي فواتير متأخرة؟',
    ask: 'اسأل',
    bankTransfer: 'تحويل بنكي',
    select: 'اختيار',
    customerAR: 'عميل (مدين)',
    supplierAP: 'مورد (دائن)',
  },
  projectsPage: {
    overview: 'نظرة عامة',
    financial: 'المالية',
    budget: 'الميزانية',
    contracts: 'العقود',
    procurement: 'المشتريات',
    documents: 'المستندات',
    timeline: 'الجدول الزمني',
    risks: 'المخاطر',
    approvals: 'الاعتمادات',
    aiInsights: 'تحليلات الذكاء الاصطناعي',
    budgetStat: 'الميزانية',
    spentStat: 'المصروف',
    contractsStat: 'العقود',
    claimsStat: 'المطالبات',
    procurementStat: 'المشتريات',
    newProject: '+ مشروع جديد',
    cancel: 'إلغاء',
    projectInformation: 'معلومات المشروع',
    code: 'الكود',
    name: 'الاسم',
    client: 'العميل',
    location: 'الموقع',
    manager: 'المدير',
    start: 'البداية',
    end: 'النهاية',
    progress: 'التقدم',
    completion: 'الإنجاز',
    budgetUsed: 'الميزانية المستخدمة',
    budgetUtilization: 'نسبة استخدام الميزانية',
    purchaseRequests: 'طلبات الشراء',
    boqItems: 'أصناف جدول الكميات',
    description: 'الوصف',
    noClient: 'لا يوجد عميل',
    totalBudget: 'إجمالي الميزانية',
    contractValue: 'قيمة العقود',
    claimsFiled: 'المطالبات المقدمة',
    prEstimated: 'المقدر من طلبات الشراء',
    financialBreakdown: 'التفصيل المالي',
    noContractsLinked: 'لا توجد عقود مرتبطة',
    budgetAllocation: 'توزيع الميزانية',
    remaining: 'المتبقي',
    boqSummary: 'ملخص جدول الكميات',
    noBoqItems: 'لا توجد أصناف في جدول الكميات',
    noContractsLinkedToProject: 'لا توجد عقود مرتبطة بهذا المشروع',
    noPurchaseRequests: 'لا توجد طلبات شراء لهذا المشروع',
    documentIntelligence: 'الذكاء المستنداتي',
    documentHint: 'ارفع العقود والرسومات وطلبات المعلومات والتقديمات',
    uploadDocument: 'رفع مستند',
    viewAll: 'عرض الكل',
    projectTimeline: 'الجدول الزمني للمشروع',
    projectCreated: 'إنشاء المشروع',
    contract: 'عقد',
    claim: 'مطالبة',
    pr: 'طلب شراء',
    budgetOverrun: 'تجاوز الميزانية',
    claimsPending: 'مطالبات معلقة',
    procurementBottleneck: 'عقدة إقليمية في المشتريات',
    high: 'عالية',
    medium: 'متوسطة',
    low: 'منخفضة',
    action: 'الإجراء',
    pendingApprovals: 'الاعتمادات المعلقة',
    approvalsHint: 'ستظهر هنا الاعتمادات المطلوبة لهذا المشروع',
    aiProjectAnalyst: 'محلل المشاريع بالذكاء الاصطناعي',
    aiProjectDesc: 'اسأل عن صحة المشروع والميزانية والمخاطر والأداء',
    aiPlaceholder: 'مثال: لماذا نسبة استخدام الميزانية مرتفعة؟',
    ask: 'اسأل',
    noProjects: 'لا توجد مشاريع بعد',
    save: 'حفظ',
    title: 'العنوان',
    status: 'الحالة',
    value: 'القيمة',
    prNumber: 'رقم طلب الشراء',
    estCost: 'التكلفة المقدرة',
  },
  contractsPage: {
    title: 'العقود',
    subtitle: 'إدارة العقود والاتفاقيات',
    newContract: 'عقد جديد',
    noContracts: 'لا توجد عقود بعد',
    backToContracts: 'العقود',
    contractsCount: 'عقود',
    totalValueLabel: 'القيمة الإجمالية',
    value: 'القيمة',
    type: 'النوع',
    project: 'المشروع',
    status: 'الحالة',
    overview: 'نظرة عامة',
    financial: 'المالية',
    timeline: 'الجدول الزمني',
    documents: 'المستندات',
    risks: 'المخاطر',
    aiInsights: 'تحليلات الذكاء الاصطناعي',
    contractDetails: 'تفاصيل العقد',
    number: 'الرقم',
    titleField: 'العنوان',
    counterpartyField: 'الطرف المقابل',
    contractValue: 'قيمة العقد',
    signed: 'تاريخ التوقيع',
    completion: 'تاريخ الإنجاز',
    contractHealth: 'صحة العقد',
    statusLabel: 'الحالة',
    contractInGoodStanding: 'العقد في وضع جيد',
    daysActive: 'عدد أيام النشاط',
    daysToCompletion: 'عدد أيام الإنجاز',
    financialSummary: 'الملخص المالي',
    invoiced: 'تم الفوترة',
    remaining: 'المتبقي',
    contractTimeline: 'الجدول الزمني للعقد',
    contractCreated: 'إنشاء العقد',
    contractSigned: 'توقيع العقد',
    expectedCompletion: 'الإنجاز المتوقع',
    notYet: 'لم يتحقق بعد',
    contractDocuments: 'مستندات العقد',
    documentsSubtitle: 'ارفع العقود الموقعة والتعديلات والمستندات ذات الصلة',
    uploadDocument: 'رفع مستند',
    contractExpiry: 'انتهاء صلاحية العقد',
    valueExposure: 'التعرض للقيمة',
    expiresLabel: 'ينتهي في',
    noExpirySet: 'لم يتم تحديد تاريخ انتهاء',
    monitorContractStatus: 'مراقبة حالة العقد',
    reviewFinancialExposure: 'مراجعة التعرض المالي',
    contractValueLabel: 'قيمة العقد',
    aiContractAnalyst: 'محلل العقود بالذكاء الاصطناعي',
    aiContractDesc: 'تحليل شروط العقد والمخاطر والتأثيرات المالية',
    aiPlaceholder: 'مثال: ما هي المخاطر الرئيسية في هذا العقد؟',
    ask: 'اسأل',
    analysisComplete: 'اكتمل التحليل.',
    analysisInitializing: 'ميزة التحليل قيد التهيئة.',
    aiConnecting: 'جارٍ الاتصال بمحرك الذكاء الاصطناعي...',
    riskAssessment: 'تقييم المخاطر',
    financialAnalysis: 'التحليل المالي',
    timelineReview: 'مراجعة الجدول الزمني',
    complianceCheck: 'فحص الامتثال',
    contractNumber: 'رقم العقد',
  },
  procurementPage: {
    tabOverview: 'نظرة عامة',
    tabRequests: 'الطلبات',
    tabSuppliers: 'الموردون',
    tabOrders: 'الأوامر',
    tabAnalysis: 'التحليل',
    tabAi: 'الذكاء الاصطناعي',
    newRequest: '+ طلب جديد',
    cancel: 'إلغاء',
    save: 'حفظ',
    totalRequests: 'إجمالي الطلبات',
    draft: 'مسودة',
    approved: 'معتمد',
    ordered: 'تم الطلب',
    priorityDistribution: 'توزيع الأولويات',
    recentRequests: 'الطلبات الأخيرة',
    noProcurementRequests: 'لا توجد طلبات مشتريات',
    requisition: 'طلب التوريد',
    title: 'العنوان',
    priority: 'الأولوية',
    status: 'الحالة',
    details: 'التفاصيل',
    estValue: 'القيمة المقدرة',
    noRequests: 'لا توجد طلبات',
    newProcurementRequest: 'طلب مشتريات جديد',
    requisitionNumber: 'رقم طلب التوريد',
    low: 'منخفض',
    medium: 'متوسط',
    high: 'عالي',
    urgent: 'عاجل',
    supplierManagement: 'إدارة الموردين',
    supplierManagementDesc: 'إدارة علاقات الموردين وأداء الموردين',
    purchaseOrders: 'أوامر الشراء',
    purchaseOrdersDesc: 'تتبع أوامر الشراء من الإنشاء إلى التسليم',
    totalValue: 'القيمة الإجمالية',
    avgPerRequest: 'المتوسط لكل طلب',
    pending: 'معلق',
    aiProcurementAdvisor: 'مستشار المشتريات بالذكاء الاصطناعي',
    aiProcurementDesc: 'تحسين قرارات المشتريات واختيار الموردين وتحليل التكاليف',
    aiPlaceholder: 'مثال: أي عناصر تحتاج مشتريات عاجلة؟',
    ask: 'اسأل',
    analysisComplete: 'اكتمل التحليل.',
    analysisInitializing: 'ميزة التحليل قيد التهيئة.',
    aiConnecting: 'جارٍ الاتصال بمحرك الذكاء الاصطناعي...',
  },
  notificationsPage: {
    title: 'الإشعارات',
    subtitle: 'إشعارات وتنبيهات النظام',
    errorLoading: 'فشل تحميل الإشعارات',
    errorMarkRead: 'فشل تحديد كمقروء',
    errorMarkAllRead: 'فشل تحديد الكل كمقروء',
    justNow: 'الآن',
    minutesAgo: 'د',
    hoursAgo: 'س',
    daysAgo: 'ي',
    unreadLabel: 'غير مقروءة',
    markAllRead: 'تحديد الكل كمقروء',
    statsTotal: 'الإجمالي',
    statsUnread: 'غير مقروءة',
    statsToday: 'اليوم',
    statsThisWeek: 'هذا الأسبوع',
    filterAll: 'الكل',
    filterUnread: 'غير مقروءة',
    filterApprovals: 'الاعتمادات',
    filterSystem: 'النظام',
    filterAlerts: 'التنبيهات',
    noNotifications: 'لا توجد إشعارات',
    allCaughtUp: 'لقد تابعت كل شيء!',
    relatedEntity: 'كيان مرتبط',
    viewRelated: 'عرض المرتبط',
    markAsRead: 'تحديد كمقروء',
    dismiss: 'تجاهل',
  },
  auditPage: {
    title: 'سجل المراجعة',
    actionLabel: 'الإجراء',
    filterByAction: 'تصفية حسب الإجراء...',
    resourceType: 'نوع المورد',
    filterByResource: 'تصفية حسب المورد...',
    clear: 'مسح',
    action: 'الإجراء',
    resourceId: 'معرف المورد',
    actor: 'الفاعل',
    timestamp: 'الوقت',
    details: 'التفاصيل',
    view: 'عرض',
  },
  documentsPage: {
    loading: 'جارٍ تحميل المستندات...',
    title: 'الذكاء المستنداتي',
    documentsCount: 'مستندات',
    total: 'الإجمالي',
    processed: 'تمت المعالجة',
    processing: 'جارٍ المعالجة',
    failed: 'فشل',
    categories: 'الفئات',
    searchPlaceholder: 'بحث في المستندات...',
    allCategories: 'جميع الفئات',
    invoice: 'فاتورة',
    receipt: 'إيصال',
    contract: 'عقد',
    purchaseOrder: 'أمر شراء',
    goodsReceived: 'بضاعة مستلمة',
    report: 'تقرير',
    other: 'أخرى',
    search: 'بحث',
    file: 'الملف',
    category: 'الفئة',
    status: 'الحالة',
    classification: 'التصنيف',
    size: 'الحجم',
    actions: 'الإجراءات',
    extract: 'استخراج',
    classify: 'تصنيف',
    po: 'طلب شراء',
    noDocumentsFound: 'لم يتم العثور على مستندات',
    categoryLabel: 'الفئة:',
    statusLabel: 'الحالة:',
    typeLabel: 'النوع:',
    mimeLabel: 'النوع الفرعي:',
    extractedData: 'البيانات المستخرجة:',
    ocrText: 'النص المستخرج:',
  },
  boqPage: {
    title: 'جدول الكميات',
    subtitle: 'إدارة بنود جدول الكميات والإصدارات',
    createBoq: 'إنشاء جدول كميات',
    editBoq: 'تعديل جدول كميات',
    contract: 'العقد',
    contractRequired: 'العقد *',
    selectContract: 'اختر العقد',
    version: 'الإصدار',
    status: 'الحالة',
    draft: 'مسودة',
    submitted: 'مقدم',
    approved: 'موافق عليه',
    confirm: 'تأكيد',
    areYouSure: 'هل أنت متأكد؟',
    failedToLoad: 'فشل في تحميل جداول الكميات',
    failedToSave: 'فشل في الحفظ',
  },
};
