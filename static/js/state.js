// ==========================================
// Job Hunter CRM — Global Application State
// ==========================================

var vacancies = [];
var profiles = [];
var currentTab = 'inbox';
var currentMarket = 'all';
var currentVac = null;
var currentProfile = 0;
var cropper = null;
var activeProfileId = null;

// Filter & Search State
var filterSearch = '';
var filterGrades = [];
var filterMatches = [];
var filterSource = 'all';
var filterSort = 'newest';
var pendingBlacklistVacId = null;
