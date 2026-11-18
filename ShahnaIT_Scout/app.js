// ============================================
// AUTHENTICATION
// ============================================
let currentUser = null;

async function checkAuth() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
            const data = await res.json();
            currentUser = data.user;
            document.getElementById('loginOverlay').style.display = 'none';
            document.getElementById('userDisplayName').textContent = currentUser.full_name || currentUser.email;
            document.getElementById('userDisplayRole').textContent = currentUser.role.toUpperCase();
            
            // Hide Users tab for non-admins
            const tabUsers = document.getElementById('tabUsers');
            if (tabUsers && currentUser.role !== 'admin') {
                tabUsers.style.display = 'none';
            }
            
            loadDashboard();
            loadUploaderDropdown();
            if (currentUser.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
            }
            if (currentUser.role === 'admin' || currentUser.role === 'manager') {
                document.querySelectorAll('.manager-only').forEach(el => el.style.display = 'block'
);
            }
        }
    } catch(e) {
        console.log('Not logged in');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentUser = data.user;
            document.getElementById('loginOverlay').style.display = 'none';
            document.getElementById('userDisplayName').textContent = currentUser.full_name || currentUser.email;
                       document.getElementById('userDisplayRole').textContent = currentUser.role.toUpperCase();
            
            // Hide Users tab for non-admins
            const tabUsers = document.getElementById('tabUsers');
            if (tabUsers && currentUser.role !== 'admin') {
                tabUsers.style.display = 'none';
            }
            
                        loadDashboard();
            if (currentUser.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
            }
            toastSuccess('Welcome, ' + currentUser.full_name + '!');
        } else {
            errorDiv.textContent = data.error || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch(e) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    }
}

async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    document.getElementById('loginOverlay').style.display = 'flex';
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
}

checkAuth();

    let allJobs = [], allCandidates = [], currentCandidateId = null;
    let currentCandidateData = null;
    let selectedBulkFiles = [];
    console.log('✅ App initialized');
console.log('✅ loadNotes:', typeof loadNotes);
console.log('✅ addNote:', typeof addNote);
console.log('✅ deleteNote:', typeof deleteNote);
console.log('✅ viewCandidate:', typeof viewCandidate);
console.log('✅ viewOriginalResume:', typeof viewOriginalResume);
// ============================================
// SIDEBAR TOGGLE FOR MOBILE
// ============================================
window.addEventListener('scroll', function() {
    const inv = document.querySelector('.candidate-inventory');
    if (inv) {
        if (window.scrollY > 50) {
            inv.classList.add('shrink');
        } else {
            inv.classList.remove('shrink');
        }
    }
});

function openMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (window.innerWidth <= 768) {
        if (sidebar.style.position !== 'fixed') {
            sidebar.style.position = 'fixed';
            sidebar.style.top = '0';
            sidebar.style.left = '-280px';
            sidebar.style.width = '260px';
            sidebar.style.height = '100vh';
            sidebar.style.zIndex = '1000';
            sidebar.style.paddingTop = '60px';
            sidebar.style.transition = 'left 0.3s ease';
        }
        sidebar.classList.toggle('open');
        sidebar.style.left = sidebar.classList.contains('open') ? '0' : '-280px';
    } else {
        sidebar.classList.toggle('open');
    }
    
    if (overlay) overlay.classList.toggle('active');
}

function toggleSidebarGroup(header) {
    header.classList.toggle('open');
    const items = header.nextElementSibling;
    items.classList.toggle('open');
}

// Close sidebar when clicking outside (on mobile)
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.querySelector('.mobile-menu-btn');
    
    if (window.innerWidth <= 768) {
        if (sidebar && !sidebar.contains(event.target) && menuBtn && !menuBtn.contains(event.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// Close sidebar when a tab is clicked (on mobile)
document.querySelectorAll('.tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.remove('open');
            }
        }
    });
});
// ============================================
// VIEW CANDIDATE - FULL MODAL VERSION
// ============================================
async function loadClientsDropdown() {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    const clients = [...new Set(jobs.map(j => j.client_name || j.company).filter(Boolean))];
    const select = document.getElementById('edit_proposed_client');
    if (select) {
        select.innerHTML = '<option value="">-- Select Client --</option>' + 
            clients.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    }
}
window.viewCandidate = function(id) {
    console.log('Opening candidate:', id);
    currentCandidateId = id;
    
    const candidate = allCandidates.find(c => c.id == id);
    if (!candidate) {
        toastError('Candidate not found');
        return;
    }
    
    currentCandidateData = candidate;
    
    // Set HR name in header
    document.getElementById('modalHRName').innerHTML = 
    '<span style="background:#fff;color:#1B2A4A;padding:3px 12px;border-radius:14px;font-weight:700;font-size:13px;margin-right:12px;">SIT-C-' + String(candidate.id).padStart(3,'0') + '</span>' +
    '<i class="fas fa-user-circle"></i> Uploaded by: ' + escapeHtml(String(candidate.uploaded_by_name || 'ShahnaIT HR'));
    document.getElementById('modalCandidateName').textContent = (candidate.first_name || '') + ' ' + (candidate.last_name || '');
    
    // AI Summary
    if (candidate.analysis_summary) {
        document.getElementById('aiSummarySection').style.display = 'block';
        document.getElementById('aiSummaryText').textContent = candidate.analysis_summary;
        document.getElementById('aiMatchedJD').textContent = candidate.matched_jd || 'Analysis';
    } else {
        document.getElementById('aiSummarySection').style.display = 'none';
    }
    
    // Basic Info
    document.getElementById('edit_first_name').value = candidate.first_name || '';
    document.getElementById('edit_last_name').value = candidate.last_name || '';
    document.getElementById('edit_email').value = candidate.email || '';
    document.getElementById('edit_phone').value = candidate.phone || '';
    document.getElementById('edit_designation').value = candidate.designation || candidate.current_role || '';
    document.getElementById('edit_linkedin').value = candidate.linkedin || '';
    document.getElementById('edit_location').value = candidate.location || candidate.address || '';
    document.getElementById('edit_years_exp').value = candidate.years_of_experience || '';
    
    // Compensation
    document.getElementById('edit_current_ctc').value = candidate.current_ctc || '';
    document.getElementById('edit_expected_ctc').value = candidate.expected_ctc || '';
    
    // Proposed
    document.getElementById('edit_proposed_client').value = candidate.proposed_client || '';
    // Requirement will be set by loadRequirementsForClient(), just store the ID
    document.getElementById('edit_proposed_requirement').value = candidate.proposed_requirement || '';
    document.getElementById('edit_proposed_requirement').setAttribute('data-saved-id', candidate.proposed_requirement || '');
    // Stage
    document.getElementById('edit_stage').value = candidate.stage || 'new';
    updateStageColor();
    
    // Skills
    renderSkills(candidate.core_skills);
    
    // Work History
    renderWorkHistory(candidate.work_experience);
    renderProjects(candidate.id);
    renderEducation(candidate.id);
    renderRelevantExperience(candidate.relevant_experience);
    
    // Certifications
    renderCertifications(candidate.certifications);
    
    // Attachments
    renderAttachments(candidate.attachments);
    
    // Resume - FULL TEXT, NO TRUNCATION
    const resumeText = candidate.resume_text || '';
    document.getElementById('resumeFullText').textContent = resumeText;
    
    // Notes
    document.getElementById('edit_notes').value = candidate.notes || '';
    
    // Load clients dropdown
    loadClientsDropdown();
    
    // Show modal
    document.getElementById('candidateModal').style.display = 'block';
};

// ============================================
// HELPER FUNCTIONS
// ============================================
function escapeHtml(str) {
    str = String(str || '');
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderSkills(skillsData) {
    const container = document.getElementById('skillsContainer');
    container.innerHTML = '';
    let skills = [];
try {
    if (skillsData) {
        skills = typeof skillsData === 'string' ? JSON.parse(skillsData) : skillsData;
    }
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];
    
    if (!Array.isArray(skills) || skills.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No skills added</span>';
        return;
    }
    
    skills.forEach((skill, index) => {
        const tag = document.createElement('span');
        tag.className = 'skill-tag editable-skill';
        tag.innerHTML = escapeHtml(String(typeof skill === 'object' ? (skill.skill || skill.name || '') : skill)) + ' <i class="fas fa-times" style="cursor:pointer;margin-left:4px;font-size:10px;" onclick="removeSkill(' + index + ')"></i>';
        container.appendChild(tag);
    });
}

function renderWorkHistory(workData) {
    const container = document.getElementById('workHistoryContainer');
    container.innerHTML = '';
    let work = [];
    try {
        work = typeof workData === 'string' ? JSON.parse(workData) : (workData || []);
    } catch(e) { work = []; }
    
    if (!Array.isArray(work) || work.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No work history</span>';
        return;
    }
    
    work.forEach((w, index) => {
        const div = document.createElement('div');
        div.className = 'company-item';
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';
        div.innerHTML = '<span><strong>' + escapeHtml(String(w.company || w || '')) + '</strong></span>' +
            '<i class="fas fa-times" style="cursor:pointer;color:#C42020;font-size:12px;" onclick="removeWorkEntry(' + index + ')"></i>';
        container.appendChild(div);
    });
}

function renderCertifications(certsData) {
    const container = document.getElementById('certificationsContainer');
    container.innerHTML = '';
    let certs = [];
    try {
        certs = typeof certsData === 'string' ? JSON.parse(certsData) : (certsData || []);
    } catch(e) { certs = []; }
    
    if (!Array.isArray(certs) || certs.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No certifications</span>';
        return;
    }
    
    certs.forEach((cert, index) => {
        const div = document.createElement('div');
        div.className = 'company-item';
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';
        div.innerHTML = '<span>📜 ' + escapeHtml(String(cert)) + '</span>' +
            '<i class="fas fa-times" style="cursor:pointer;color:#C42020;font-size:12px;" onclick="removeCertification(' + index + ')"></i>';
        container.appendChild(div);
    });
}
function renderAttachments(attachmentsData) {
    const container = document.getElementById('attachmentsList');
    if (!container) return;
    container.innerHTML = '';
    
    let attachments = [];
    try {
        attachments = typeof attachmentsData === 'string' ? JSON.parse(attachmentsData) : (attachmentsData || []);
    } catch(e) { attachments = []; }
    
    if (!Array.isArray(attachments) || attachments.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No attachments</span>';
        return;
    }
    
    attachments.forEach((att, index) => {
        const filename = att.filename || att.original_name || att;
        const div = document.createElement('div');
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:13px;border-bottom:1px solid #E2E8F0;';
        div.innerHTML = '<span>📎 ' + escapeHtml(String(filename)) + '</span>' +
            '<div style="display:flex;gap:8px;">' +
'<i class="fas fa-eye" style="cursor:pointer;color:#2C7A4A;" onclick="viewAttachment(&quot;' + escapeHtml(String(filename)) + '&quot;)" title="View"></i>' +
'<i class="fas fa-download" style="cursor:pointer;color:#1B2A4A;" onclick="downloadAttachment(&quot;' + escapeHtml(String(filename)) + '&quot;)" title="Download"></i>' +
'<i class="fas fa-trash" style="cursor:pointer;color:#C42020;" onclick="deleteAttachment(&quot;' + escapeHtml(String(filename)) + '&quot;)" title="Delete"></i>' +
            '</div>';
        container.appendChild(div);
    });
}

function downloadAttachment(filename) {
    if (!currentCandidateId) return;
    window.open('/api/candidates/' + currentCandidateId + '/attachments/' + filename, '_blank');
}

function viewAttachment(filename) {
    if (!currentCandidateId) return;
    window.open('/api/candidates/' + currentCandidateId + '/attachments/' + filename + '?view=1', '_blank');
}

async function deleteAttachment(filename) {
    if (!currentCandidateId) return;
    if (!confirm('Delete "' + filename + '"?')) return;
    
    try {
        const res = await fetch('/api/candidates/' + currentCandidateId + '/attachments/' + filename, {
            method: 'DELETE'
        });
        const result = await res.json();
        
        if (result.success) {
            toastSuccess('File deleted');
            const candidateRes = await fetch('/api/candidates/' + currentCandidateId);
            const candidate = await candidateRes.json();
            currentCandidateData = candidate;
            renderAttachments(candidate.attachments);
        } else {
            toastError('Failed to delete');
        }
    } catch(e) {
        toastError('Error: ' + e.message);
    }
}

function updateStageColor() {
    const stage = document.getElementById('edit_stage').value;
    const colorBar = document.getElementById('stageColorBar');
    const colors = {
        'new': '#1B5F8C',
        'proposed': '#6B4CB8',
        'screening': '#B85C00',
        'technical_l1': '#0D7B4A',
        'technical_l2': '#0D7B4A',
        'technical_l3': '#0A5C35',
        'rejected': '#C42020',
        'shortlisted': '#D4A800',
        'offer_letter_shared': '#2C7A4A',
        'onboarded': '#1B5F8C'
    };
    colorBar.style.background = colors[stage] || '#1B2A4A';
}

// Skill Management
function addSkillToCandidate() {
    const input = document.getElementById('newSkillInput');
    const rawSkill = input.value.trim();
    if (!rawSkill) return;
    
    let skills = [];
    try {
        skills = typeof currentCandidateData.core_skills === 'string' ? JSON.parse(currentCandidateData.core_skills) : (currentCandidateData.core_skills || []);
    } catch(e) { skills = []; }
    if (!Array.isArray(skills)) skills = [];
    
        // Split by comma and add each skill separately, avoiding duplicates
    const newSkills = rawSkill.split(',').map(s => s.trim()).filter(s => s);
    newSkills.forEach(skill => {
        const exists = skills.some(s => 
            (typeof s === 'string' && s.toLowerCase() === skill.toLowerCase()) ||
            (typeof s === 'object' && s.skill && s.skill.toLowerCase() === skill.toLowerCase())
        );
        if (!exists) {
            skills.push(skill);
        }
    });
    
    currentCandidateData.core_skills = skills;
    renderSkills(skills);
    input.value = '';
}

function removeSkill(index) {
let skills = [];
try {
    skills = typeof currentCandidateData.core_skills === 'string' ? JSON.parse(currentCandidateData.core_skills) : (currentCandidateData.core_skills || []);
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];
skills.splice(index, 1);
    currentCandidateData.core_skills = skills;
    renderSkills(skills);
}

function renderRelevantExperience(data) {
    const container = document.getElementById('relevantExperienceContainer');
    if (!container) return;
    container.innerHTML = '';
    let exp = [];
    try {
        exp = typeof data === 'string' ? JSON.parse(data) : (data || []);
    } catch(e) { exp = []; }
    if (!Array.isArray(exp) || exp.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No relevant experience</span>';
        return;
    }
    exp.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'company-item';
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';
        div.innerHTML = `<span>💼 <strong>${escapeHtml(item.skill || '')}</strong> - ${item.years || 0} years</span>
            <i class="fas fa-times" style="cursor:pointer;color:#C42020;font-size:12px;" onclick="removeRelevantExperience(${index})"></i>`;
        container.appendChild(div);
    });
}

function addRelevantExperience() {
    const skillInput = document.getElementById('relevantSkillInput');
    const yearsInput = document.getElementById('relevantYearsInput');
    const skill = skillInput.value.trim();
    const years = parseInt(yearsInput.value) || 0;
    if (!skill) return;
    
    let exp = [];
    try {
        exp = typeof currentCandidateData.relevant_experience === 'string' ? JSON.parse(currentCandidateData.relevant_experience) : (currentCandidateData.relevant_experience || []);
    } catch(e) { exp = []; }
    if (!Array.isArray(exp)) exp = [];
    
    exp.push({skill: skill, years: years});
    currentCandidateData.relevant_experience = exp;
    renderRelevantExperience(exp);
    skillInput.value = '';
    yearsInput.value = '';
}

function removeRelevantExperience(index) {
    let exp = [];
    try {
        exp = typeof currentCandidateData.relevant_experience === 'string' ? JSON.parse(currentCandidateData.relevant_experience) : (currentCandidateData.relevant_experience || []);
    } catch(e) { exp = []; }
    exp.splice(index, 1);
    currentCandidateData.relevant_experience = exp;
    renderRelevantExperience(exp);
}

// ============ PROJECTS ============
async function renderProjects(candidateId) {
    const container = document.getElementById('projectsContainer');
    if (!container) return;
    const res = await fetch('/api/candidates/' + candidateId + '/projects');
    const projects = await res.json();
    
    if (!projects.length) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No projects added</span>';
        return;
    }
    
    container.innerHTML = projects.map(p => `
        <div class="company-item" style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <strong>${escapeHtml(p.project_name)}</strong> ${p.role ? '| ' + escapeHtml(p.role) : ''} ${p.start_date ? '| ' + escapeHtml(p.start_date) + ' - ' + escapeHtml(p.end_date || 'Present') : ''}
                </div>
                <div style="display:flex;gap:6px;">
                    <i class="fas fa-edit" style="cursor:pointer;color:#1B2A4A;" onclick="editProjectEntry(${p.id}, ${candidateId})"></i>
                    <i class="fas fa-trash" style="cursor:pointer;color:#C42020;" onclick="deleteProjectEntry(${p.id}, ${candidateId})"></i>
                </div>
            </div>
        </div>
    `).join('');
}

function addProjectEntry() {
    const candidateId = currentCandidateId;
    const projectText = prompt('Enter project (e.g., E-commerce Platform, Lead Developer, Jun 2022 - Present):');
    if (!projectText) return;
    
    const parts = projectText.split(',').map(p => p.trim());
    const projectName = parts[0] || '';
    const role = parts[1] || '';
    const dates = parts[2] || '';
    
    fetch('/api/candidates/' + candidateId + '/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            project_name: projectName,
            role: role,
            organization: '',
            start_date: dates.split('-')[0]?.trim() || '',
            end_date: dates.split('-')[1]?.trim() || '',
            description: '',
            tech_stack: ''
        })
    }).then(() => { renderProjects(candidateId); toastSuccess('Project added!'); });
}

function editProjectEntry(projectId, candidateId) {
    const projectName = prompt('Project Name:', '');
    if (!projectName) return;
    const role = prompt('Role:', '');
    const org = prompt('Organization:', '');
    const start = prompt('Start Date:', '');
    const end = prompt('End Date:', '');
    const desc = prompt('Description:', '');
    const tech = prompt('Tech Stack:', '');
    
    fetch('/api/candidates/projects/' + projectId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: projectName, role, organization: org, start_date: start, end_date: end, description: desc, tech_stack: tech})
    }).then(() => { renderProjects(candidateId); toastSuccess('Project updated!'); });
}

function deleteProjectEntry(projectId, candidateId) {
    if (!confirm('Delete this project?')) return;
    fetch('/api/candidates/projects/' + projectId, { method: 'DELETE' })
        .then(() => { renderProjects(candidateId); toastSuccess('Project deleted'); });
}

// ============ EDUCATION ============
async function renderEducation(candidateId) {
    const container = document.getElementById('educationContainer');
    if (!container) return;
    const res = await fetch('/api/candidates/' + candidateId + '/education-entries');
    const education = await res.json();
    
    if (!education.length) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No education added</span>';
        return;
    }
    
    container.innerHTML = education.map(e => `
        <div class="company-item" style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <strong>${escapeHtml(e.degree)}</strong> | ${escapeHtml(e.institute)} ${e.start_year ? '| ' + escapeHtml(e.start_year) + ' - ' + escapeHtml(e.end_year || 'Present') : ''}
                </div>
                <div style="display:flex;gap:6px;">
                    <i class="fas fa-edit" style="cursor:pointer;color:#1B2A4A;" onclick="editEducationEntry(${e.id}, ${candidateId})"></i>
                    <i class="fas fa-trash" style="cursor:pointer;color:#C42020;" onclick="deleteEducationEntry(${e.id}, ${candidateId})"></i>
                </div>
            </div>
        </div>
    `).join('');
}

function addEducationEntry() {
    const candidateId = currentCandidateId;
    const educationText = prompt('Enter education (e.g., B.Tech CSE, IIT Bombay, 2016-2020):');
    if (!educationText) return;
    
    const parts = educationText.split(',').map(p => p.trim());
    const degree = parts[0] || '';
    const institute = parts[1] || '';
    const years = parts[2] || '';
    
    fetch('/api/candidates/' + candidateId + '/education-entries', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            degree: degree,
            institute: institute,
            start_year: years.split('-')[0]?.trim() || '',
            end_year: years.split('-')[1]?.trim() || '',
            field_of_study: '',
            grade: '',
            location: ''
        })
    }).then(() => { renderEducation(candidateId); toastSuccess('Education added!'); });
}

function editEducationEntry(eduId, candidateId) {
    const degree = prompt('Degree:', '');
    if (!degree) return;
    const institute = prompt('Institute:', '');
    if (!institute) return;
    const field = prompt('Field of Study:', '');
    const start = prompt('Start Year:', '');
    const end = prompt('End Year:', '');
    const grade = prompt('Grade:', '');
    const location = prompt('Location:', '');
    
    fetch('/api/candidates/education/' + eduId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({degree, institute, field_of_study: field, start_year: start, end_year: end, grade, location})
    }).then(() => { renderEducation(candidateId); toastSuccess('Education updated!'); });
}

function deleteEducationEntry(eduId, candidateId) {
    if (!confirm('Delete this education entry?')) return;
    fetch('/api/candidates/education/' + eduId, { method: 'DELETE' })
        .then(() => { renderEducation(candidateId); toastSuccess('Education deleted'); });
}

function addWorkEntry() {
    const company = prompt('Enter company name:');
    if (!company) return;
let work = [];
try {
    work = typeof currentCandidateData.work_experience === 'string' ? JSON.parse(currentCandidateData.work_experience) : (currentCandidateData.work_experience || []);
} catch(e) { work = []; }
if (!Array.isArray(work)) work = [];
work.push({company: company});
    currentCandidateData.work_experience = work;
    renderWorkHistory(work);
}

function removeWorkEntry(index) {
    let work = [];
    try {
        work = typeof currentCandidateData.work_experience === 'string' ? JSON.parse(currentCandidateData.work_experience) : (currentCandidateData.work_experience || []);
    } catch(e) { work = []; }
    work.splice(index, 1);
    currentCandidateData.work_experience = work;
    renderWorkHistory(work);
}

function addCertification() {
    const cert = prompt('Enter certification name:');
    if (!cert) return;
let certs = [];
try {
    certs = typeof currentCandidateData.certifications === 'string' ? JSON.parse(currentCandidateData.certifications) : (currentCandidateData.certifications || []);
} catch(e) { certs = []; }
if (!Array.isArray(certs)) certs = [];
certs.push(cert);
    currentCandidateData.certifications = certs;
    renderCertifications(certs);
}

function removeCertification(index) {
    let certs = [];
    try {
        certs = typeof currentCandidateData.certifications === 'string' ? JSON.parse(currentCandidateData.certifications) : (currentCandidateData.certifications || []);
    } catch(e) { certs = []; }
    certs.splice(index, 1);
    currentCandidateData.certifications = certs;
    renderCertifications(certs);
}

function removeAttachment(index) {
    let attachments = [];
    try {
        attachments = typeof currentCandidateData.attachments === 'string' ? JSON.parse(currentCandidateData.attachments) : (currentCandidateData.attachments || []);
    } catch(e) { attachments = []; }
    attachments.splice(index, 1);
    currentCandidateData.attachments = attachments;
    renderAttachments(attachments);
}

async function uploadAttachments() {
    const fileInput = document.getElementById('attachmentFileInput');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        toastError('Please select files first');
        return;
    }
    
    const files = fileInput.files;
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('/api/candidates/' + currentCandidateId + '/attachments', {
                method: 'POST',
                body: formData
            });
            const result = await res.json();
            
            if (result.success) {
                successCount++;
                // Update attachments in current data
                currentCandidateData.attachments = result.attachments;
            } else {
                failCount++;
            }
        } catch(e) {
            failCount++;
        }
    }
    
    // Refresh the attachments list
    renderAttachments(currentCandidateData.attachments);
    
    // Reset file input
    fileInput.value = '';
    
    if (successCount > 0) {
        toastSuccess(successCount + ' file(s) uploaded!');
    }
    if (failCount > 0) {
        toastError(failCount + ' file(s) failed');
    }
}

// Save Changes
async function saveCandidateChanges() {
    if (!currentCandidateId) return;
    
    const data = {
        first_name: document.getElementById('edit_first_name').value,
        last_name: document.getElementById('edit_last_name').value,
        email: document.getElementById('edit_email').value,
        phone: document.getElementById('edit_phone').value,
        designation: document.getElementById('edit_designation').value,
        linkedin: document.getElementById('edit_linkedin').value,
        location: document.getElementById('edit_location').value,
        years_of_experience: document.getElementById('edit_years_exp').value,
        current_ctc: document.getElementById('edit_current_ctc').value,
        expected_ctc: document.getElementById('edit_expected_ctc').value,
        proposed_client: document.getElementById('edit_proposed_client').value,
        proposed_requirement: (document.getElementById('edit_proposed_requirement').value || '').split(' - ')[0].trim(),
        stage: document.getElementById('edit_stage').value,
        notes: document.getElementById('edit_notes').value,
    core_skills: (() => {
        let s = currentCandidateData.core_skills;
        if (typeof s === 'string') {
           try { s = JSON.parse(s); } catch(e) { s = []; }
           if (typeof s === 'string') {
               try { s = JSON.parse(s); } catch(e) { s = []; }
          }
    }
    return Array.isArray(s) ? s : [];
})(),
                work_experience: (() => {
            let s = currentCandidateData.work_experience;
            if (typeof s === 'string') {
                try { s = JSON.parse(s); } catch(e) { s = []; }
                if (typeof s === 'string') { try { s = JSON.parse(s); } catch(e) { s = []; } }
            }
            return Array.isArray(s) ? s : [];
        })(),
        relevant_experience: (() => {
            let s = currentCandidateData.relevant_experience;
            if (typeof s === 'string') {
                try { s = JSON.parse(s); } catch(e) { s = []; }
                if (typeof s === 'string') { try { s = JSON.parse(s); } catch(e) { s = []; } }
            }
            return Array.isArray(s) ? s : [];
        })(),
        certifications: (() => {
            let s = currentCandidateData.certifications;
            if (typeof s === 'string') {
                try { s = JSON.parse(s); } catch(e) { s = []; }
                if (typeof s === 'string') { try { s = JSON.parse(s); } catch(e) { s = []; } }
            }
            return Array.isArray(s) ? s : [];
        })(),
        attachments: (() => {
            let s = currentCandidateData.attachments;
            if (typeof s === 'string') {
                try { s = JSON.parse(s); } catch(e) { s = []; }
                if (typeof s === 'string') { try { s = JSON.parse(s); } catch(e) { s = []; } }
            }
            return Array.isArray(s) ? s : [];
        })(),
    };
    
    try {
        const response = await fetch('/api/candidates/' + currentCandidateId, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            toastSuccess('Candidate updated successfully!');
            closeModal();
            loadCandidates();
        } else {
            toastError(result.error || 'Update failed');
        }
    } catch(e) {
        toastError('Error: ' + e.message);
    }
}

// PDF Generation
function generateCandidatePDF() {
    const candidate = currentCandidateData;
    if (!candidate) return;
    
    let html = '<html><head><meta charset="UTF-8"><style>';
    html += 'body{font-family:"Times New Roman",serif;font-size:12pt;color:#000;padding:40px;line-height:1.6;}';
    html += 'h1{font-size:20pt;color:#1B2A4A;border-bottom:2px solid #1B2A4A;padding-bottom:10px;}';
    html += 'h2{font-size:14pt;color:#1B2A4A;margin-top:20px;}';
    html += 'table{width:100%;border-collapse:collapse;margin:10px 0;}';
    html += 'td{padding:6px 10px;border:1px solid #ccc;}';
    html += 'td:first-child{font-weight:bold;background:#f5f5f5;width:30%;}';
    html += '.skill-tag{display:inline-block;background:#E8EDF5;color:#1B2A4A;padding:3px 10px;margin:3px;border-radius:12px;font-size:10pt;}';
    html += '.section{margin:15px 0;}';
    html += '</style></head><body>';
    
    html += '<h1>Candidate Profile: ' + escapeHtml(String(candidate.first_name + ' ' + candidate.last_name)) + '</h1>';
    
    html += '<h2>Basic Information</h2><table>';
    html += '<tr><td>Name</td><td>' + escapeHtml(String(candidate.first_name + ' ' + candidate.last_name)) + '</td></tr>';
    html += '<tr><td>Email</td><td>' + escapeHtml(String(candidate.email || 'N/A')) + '</td></tr>';
    html += '<tr><td>Phone</td><td>' + escapeHtml(String(candidate.phone || 'N/A')) + '</td></tr>';
    html += '<tr><td>Designation</td><td>' + escapeHtml(String(candidate.designation || candidate.current_role || 'N/A')) + '</td></tr>';
    html += '<tr><td>LinkedIn</td><td>' + escapeHtml(String(candidate.linkedin || 'N/A')) + '</td></tr>';
    html += '<tr><td>Location</td><td>' + escapeHtml(String(candidate.location || candidate.address || 'N/A')) + '</td></tr>';
    html += '<tr><td>Experience</td><td>' + escapeHtml(String(candidate.years_of_experience || 'N/A')) + '</td></tr>';
    html += '<tr><td>Current CTC</td><td>' + escapeHtml(String(candidate.current_ctc || 'N/A')) + '</td></tr>';
    html += '<tr><td>Expected CTC</td><td>' + escapeHtml(String(candidate.expected_ctc || 'N/A')) + '</td></tr>';
    html += '<tr><td>Stage</td><td>' + escapeHtml(String(candidate.stage || 'new')) + '</td></tr>';
    html += '</table>';
    
    // Skills
    let skills = [];
    try { skills = typeof candidate.core_skills === 'string' ? JSON.parse(candidate.core_skills) : (candidate.core_skills || []); } catch(e) {}
    if (skills.length > 0) {
        html += '<h2>Skills</h2><div>';
        skills.forEach(s => { html += '<span class="skill-tag">' + escapeHtml(String(s)) + '</span>'; });
        html += '</div>';
    }
    
    html += '<h2>Notes</h2><p>' + escapeHtml(String(candidate.notes || 'No notes')) + '</p>';
    html += '<p style="margin-top:30px;font-size:9pt;color:#666;">Generated by ShahnaIT Scout</p>';
    html += '</body></html>';
    
    const blob = new Blob([html], {type: 'text/html'});
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    toastSuccess('PDF report opened in new tab. Use Ctrl+P to save as PDF.');
}

async function runAIAnalysis() {
    if (!currentCandidateId || !currentCandidateData) {
        toastError('No candidate selected');
        return;
    }
    
    const requirementId = (document.getElementById('edit_proposed_requirement').value || '').split(' - ')[0].trim();
    if (!requirementId) {
        toastError('Please select a Requirement/Job ID first');
        return;
    }
    
    try {
        const reqRes = await fetch('/api/requirements');
        const requirements = await reqRes.json();
        const selectedReq = requirements.find(r => r.requirement_id === requirementId);
        
        if (!selectedReq) {
            toastError('Requirement not found');
            return;
        }
        
        const jobsRes = await fetch('/api/jobs');
        const jobs = await jobsRes.json();
        const job = jobs.find(j => (j.requirement_id === requirementId || j.title === selectedReq.title));
        
        const jdText = (job ? job.description : '') || selectedReq.title || '';
        const resumeText = currentCandidateData.resume_text || '';
        
        if (!resumeText) {
            toastError('No resume text available');
            return;
        }
        
        toastInfo('Running AI Analysis...');
        
        const analysisRes = await fetch('/api/analyze-match', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
body: JSON.stringify({
    resume_text: resumeText,
    jd_text: jdText,
    candidate_id: currentCandidateId,
    candidate_name: (currentCandidateData.first_name || '') + ' ' + (currentCandidateData.last_name || ''),
    job_title: job ? job.title : ''
})
        });
        
        const result = await analysisRes.json();
        
        if (result.match_score !== undefined) {
            document.getElementById('aiSummarySection').style.display = 'block';
            const summaryText = result.detailed_analysis || result.executive_summary || 'Analysis complete'; document.getElementById('aiSummaryText').textContent = summaryText;
            document.getElementById('aiMatchedJD').textContent = requirementId;
            
            currentCandidateData.analysis_summary = result.executive_summary;
            currentCandidateData.match_score = result.match_score;
            currentCandidateData.matched_jd = requirementId;
            
            await fetch('/api/candidates/' + currentCandidateId, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    analysis_summary: result.executive_summary,
                    match_score: result.match_score,
                    matched_jd: requirementId,
                    proposed_requirement: requirementId
                })
            });
            
            toastSuccess('Analysis complete! Match: ' + result.match_score + '%');
            closeModal();
            loadCandidates();
        } else {
            toastError('Analysis failed');
        }
    } catch(e) {
        toastError('Error: ' + e.message);
    }
}

function copyResumeText() {
    const text = document.getElementById('resumeFullText').textContent;
    navigator.clipboard.writeText(text).then(() => {
        toastSuccess('Resume text copied!');
    }).catch(() => {
        toastError('Failed to copy');
    });
}

function downloadOriginalResume(candidateId) {
    if (!candidateId) return;
    window.open('/api/candidates/' + candidateId + '/download-resume', '_blank');
}

function closeModal() {
    document.getElementById('candidateModal').style.display = 'none';
    currentCandidateId = null;
    currentCandidateData = null;
}

console.log('✅ viewCandidate (full modal) defined');
console.log('✅ Stage colors:', typeof updateStageColor);
console.log('✅ Skills renderer:', typeof renderSkills);
// LOAD CANDIDATES
// ============================================
async function loadCandidates() {
    try {
        const res = await fetch('/api/candidates');
        const data = await res.json();
        allCandidates = data;
        console.log('✅ Loaded ' + allCandidates.length + ' candidates');
        
        // Update the candidate cards with IDs
        document.querySelectorAll('.candidate-card').forEach(function(card) {
            const id = card.getAttribute('data-id');
            if (id) {
               if (card) card.onclick = function() {
                    viewCandidate(parseInt(id));
                };
            }
        });
    } catch (e) {
        console.error('Error loading candidates:', e);
    }
}
console.log('✅ loadCandidates defined');

// Call loadCandidates when page loads
loadCandidates();

async function loadUploaderDropdown() {
    const res = await fetch('/api/uploaders');
    const uploaders = await res.json();
    const select = document.getElementById('uploaderSelect');
    const bulkSelect = document.getElementById('bulkUploaderSelect');
    const options = '<option value="">-- Select Uploader --</option>' + 
        uploaders.map(u => `<option value="${escapeHtml(u)}">${escapeHtml(u)}</option>`).join('');
    if (select) select.innerHTML = options;
    if (bulkSelect) bulkSelect.innerHTML = options;
}

// Open first sidebar group by default
document.querySelector('.sidebar-group-header').classList.add('open');
document.querySelector('.sidebar-group-items').classList.add('open');
// ============================================
    // DARK MODE
    // ============================================
    function toggleDarkMode() {
        const body = document.body;
        const toggle = document.querySelector('.dark-mode-toggle');
        
        body.classList.toggle('dark-mode');
        
        // Save preference
        if (body.classList.contains('dark-mode')) {
            localStorage.setItem('darkMode', 'enabled');
            if (toggle) toggle.textContent = '☀️';
        } else {
            localStorage.setItem('darkMode', 'disabled');
            if (toggle) toggle.textContent = '🌙';
        }
    }

    // Load saved preference on page load
    function loadDarkModePreference() {
        const darkMode = localStorage.getItem('darkMode');
        const toggle = document.querySelector('.dark-mode-toggle');
        
        if (darkMode === 'enabled') {
            document.body.classList.add('dark-mode');
            if (toggle) toggle.textContent = '☀️';
        }
    }

    // Call on page load
    loadDarkModePreference();

    // ============================================
    // TOAST NOTIFICATIONS
    // ============================================
    function showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer');
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.add('toast-hidden');
                setTimeout(() => toast.remove(), 500);
            }
        }, duration);
        
        toast.addEventListener('click', function(e) {
            if (e.target.tagName !== 'BUTTON') {
                this.classList.add('toast-hidden');
                setTimeout(() => this.remove(), 500);
            }
        });
    }

    // Shortcut functions
    function toastSuccess(msg) { showToast(msg, 'success'); }
    function toastError(msg) { showToast(msg, 'error'); }
    function toastWarning(msg) { showToast(msg, 'warning'); }
    function toastInfo(msg) { showToast(msg, 'info'); }

    
    // Tab switching
    const tabJobs = document.getElementById('tabJobs'); if (tabJobs) tabJobs.onclick = function() { showPanel('jobs'); loadJobs(); };
    const tabCandidates = document.getElementById('tabCandidates'); if (tabCandidates) tabCandidates.onclick = function() { showPanel('candidates'); loadCandidates(); };
    const tabUpload = document.getElementById('tabUpload'); if (tabUpload) tabUpload.onclick = function() { showPanel('upload'); };
    const tabCreateJob = document.getElementById('tabCreateJob'); if (tabCreateJob) tabCreateJob.onclick = function() { showPanel('createJob'); };     const tabInterviews = document.getElementById('tabInterviews'); if (tabInterviews) tabInterviews.onclick = function() { showPanel('interviews'); loadInterviews(); };
    const tabAnalyze = document.getElementById('tabAnalyze'); if (tabAnalyze) tabAnalyze.onclick = function() { showPanel('analyze'); loadJobs(); loadCandidates(); };
    const tabDashboard = document.getElementById('tabDashboard'); const tabKanban = document.getElementById('tabKanban'); const tabReports = document.getElementById('tabReports'); if (tabReports) tabReports.onclick = function() { showPanel('reports'); document.getElementById('reportDate').value = new Date().toISOString().split('T')[0]; loadDailyReport(); }; if (tabKanban) tabKanban.onclick = function() { showPanel('kanban'); loadKanban(); }; if (tabDashboard) tabDashboard.onclick = function() { showPanel('dashboard'); loadDashboard(); };
    const tabUsers = document.getElementById('tabUsers'); if (tabUsers) tabUsers.onclick = function() { showPanel('users'); loadUsers(); };
    const tabClients = document.getElementById('tabClients'); if (tabClients) tabClients.onclick = function() { showPanel('clients'); loadClients(); };
    const tabOnboarded = document.getElementById('tabOnboarded'); const tabFinance = document.getElementById('tabFinance'); const tabInvoices = document.getElementById('tabInvoices'); const tabExpenses = document.getElementById('tabExpenses'); const tabReportsFull = document.getElementById('tabReportsFull'); if (tabReportsFull) tabReportsFull.onclick = function() { showPanel('reportsFull'); }; if (tabExpenses) tabExpenses.onclick = function() { showPanel('expenses'); loadExpenses(); }; if (tabInvoices) tabInvoices.onclick = function() { showPanel('invoices'); loadInvoices(); }; if (tabFinance) tabFinance.onclick = function() { showPanel('finance'); loadFinance(); }; if (tabOnboarded) tabOnboarded.onclick = function() { showPanel('onboarded'); loadOnboarded(); };
    
   function showPanel(panel) {
    const allPanels = ['jobsPanel', 'candidatesPanel', 'uploadPanel', 'createJobPanel', 'interviewsPanel', 'analyzePanel', 'dashboardPanel', 'kanbanPanel', 'reportsPanel', 'proposalReportsPanel', 'usersPanel', 'clientsPanel', 'onboardedPanel', 'financePanel', 'invoicesPanel', 'expensesPanel', 'reportsFullPanel'];
    allPanels.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    
    const target = document.getElementById(panel + 'Panel');
    if (target) target.style.display = 'block';
    
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
     const tabMap = {
        'jobs': 'tabJobs', 'candidates': 'tabCandidates', 'upload': 'tabUpload',
        'createJob': 'tabCreateJob', 'analyze': 'tabAnalyze', 'dashboard': 'tabDashboard',
        'interviews': 'tabInterviews', 'kanban': 'tabKanban', 'reports': 'tabReports',
        'users': 'tabUsers', 'onboarded': 'tabOnboarded', 'finance': 'tabFinance', 'proposalReports': 'tabProposalReports'
    };
    const tab = document.getElementById(tabMap[panel]);
    if (tab) tab.classList.add('active');
}
// ============================================
// INTERVIEW TRACKER FUNCTIONS
// ============================================

async function loadInterviews() {
    const dateFilter = document.getElementById('intFilterDate').value || '';
    const roundFilter = document.getElementById('intFilterRound').value || '';
    const verdictFilter = document.getElementById('intFilterVerdict').value || '';
    
    let url = '/api/interviews?';
    if (dateFilter) url += 'date=' + dateFilter + '&';
    if (roundFilter) url += 'round=' + roundFilter + '&';
    if (verdictFilter) url += 'verdict=' + verdictFilter + '&';
    
    const res = await fetch(url);
    const interviews = await res.json();
    const container = document.getElementById('interviewsList');
    
    if (!interviews.length) {
        container.innerHTML = '<div class="card no-click" style="text-align:center;padding:40px;color:#94A3B8;">📅 No interviews found</div>';
        return;
    }
    
    container.innerHTML = interviews.map(i => {
        const verdictColors = {
            'Scheduled': '#2196F3', 'Selected': '#4CAF50', 'Rejected': '#F44336',
            'Hold': '#FF9800', 'No Show': '#9E9E9E', 'Rescheduled': '#9C27B0'
        };
        const verdictColor = verdictColors[i.verdict] || '#2196F3';
        
        return `<div class="card" style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:10px;">
                <div style="flex:1;min-width:200px;">
                    <h4 style="margin:0 0 5px 0;">
                        <a href="javascript:void(0)" onclick="viewCandidate(${i.candidate_id})" style="color:#1B2A4A;text-decoration:underline;">${escapeHtml(i.candidate_name || 'Unknown')}</a>
                    </h4>
                    <div style="display:flex;gap:10px;flex-wrap:wrap;font-size:13px;color:#555;">
                        <span>📅 ${i.interview_date} ${i.interview_time || ''}</span>
                        <span style="background:#E3F2FD;padding:2px 10px;border-radius:12px;">🎯 ${escapeHtml(i.round)}</span>
                        ${i.client_name ? `<span>🏢 ${escapeHtml(i.client_name)}</span>` : ''}
                        ${i.requirement_id ? `<span>📋 ${escapeHtml(i.requirement_id)}</span>` : ''}
                    </div>
                    <div style="margin-top:8px;font-size:12px;color:#777;">
                        ${i.resource_owner ? `👤 Owner: ${escapeHtml(i.resource_owner)}` : ''}
                        ${i.client_poc ? ` | 📞 POC: ${escapeHtml(i.client_poc)}` : ''}
                    </div>
                </div>
                <div style="text-align:right;">
                    <select onchange="updateInterviewVerdict(${i.id}, this.value)" style="background:${verdictColor};color:#fff;border:none;padding:6px 12px;border-radius:16px;font-weight:bold;cursor:pointer;font-size:13px;">
                        <option value="Scheduled" ${i.verdict==='Scheduled'?'selected':''}>📋 Scheduled</option>
                        <option value="Selected" ${i.verdict==='Selected'?'selected':''}>✅ Selected</option>
                        <option value="Rejected" ${i.verdict==='Rejected'?'selected':''}>❌ Rejected</option>
                        <option value="Hold" ${i.verdict==='Hold'?'selected':''}>⏸️ Hold</option>
                        <option value="No Show" ${i.verdict==='No Show'?'selected':''}>🚫 No Show</option>
                        <option value="Rescheduled" ${i.verdict==='Rescheduled'?'selected':''}>🔄 Rescheduled</option>
                    </select>
                </div>
            </div>
           ${i.feedback ? `<div style="margin-top:8px;padding:8px;background:#F5F5F5;border-radius:6px;font-size:13px;color:#555;">💬 ${escapeHtml(i.feedback)}</div>` : ''}
            <div style="margin-top:8px;display:flex;gap:6px;">
                <button class="btn btn-sm" onclick="sendInterviewEmail(${i.id}, 'invite')" style="font-size:11px;padding:4px 10px;">📧 Send Invite</button>
                ${i.verdict !== 'Scheduled' ? `<button class="btn btn-sm btn-secondary" onclick="sendInterviewEmail(${i.id}, 'verdict')" style="font-size:11px;padding:4px 10px;">📨 Send Verdict</button>` : ''}
            </div>
        </div>`;
    }).join('');
    
    const reqList = document.getElementById('intReqList');
    if (reqList && allJobs.length) {
        reqList.innerHTML = allJobs.map(j => `<option value="${escapeHtml(j.requirement_id || 'SIT-R-' + String(j.id).padStart(3,'0'))}">`).join('');
    }
}

function searchInterviewCandidate() {
    const search = document.getElementById('intCandidateSearch').value.toLowerCase();
    const list = document.getElementById('intCandidateList');
    if (!search || search.length < 2) { list.innerHTML = ''; return; }
    const matches = allCandidates.filter(c => 
        (c.first_name + ' ' + c.last_name).toLowerCase().includes(search) ||
        ('SIT-C-' + String(c.id).padStart(3,'0')).includes(search)
    );
    list.innerHTML = matches.map(c => 
        `<option value="${escapeHtml('SIT-C-' + String(c.id).padStart(3,'0') + ' - ' + (c.first_name||'') + ' ' + (c.last_name||''))}">`
    ).join('');
}

async function scheduleInterview() {
    const candidateVal = document.getElementById('intCandidateSearch').value;
    const candidateId = candidateVal.split(' - ')[0].replace('SIT-C-', '').trim();
    
    if (!candidateId) { toastError('Please select a candidate'); return; }
    
    const data = {
        candidate_id: parseInt(candidateId),
        candidate_name: candidateVal.split(' - ').slice(1).join(' - ').trim(),
        interview_date: document.getElementById('intDate').value,
        interview_time: document.getElementById('intTime').value,
        round: document.getElementById('intRound').value,
        resource_owner: document.getElementById('intOwner').value,
        client_name: document.getElementById('intClient').value,
        client_poc: document.getElementById('intPOC').value,
        requirement_id: document.getElementById('intRequirement').value,
        scheduled_by: 'HR'
    };
    
    if (!data.interview_date) { toastError('Please select a date'); return; }
    
    const res = await fetch('/api/interviews', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        toastSuccess('Interview scheduled!');
        document.getElementById('intCandidateSearch').value = '';
        document.getElementById('intDate').value = '';
        document.getElementById('intTime').value = '';
        document.getElementById('intOwner').value = '';
        document.getElementById('intClient').value = '';
        document.getElementById('intPOC').value = '';
        document.getElementById('intRequirement').value = '';
        loadInterviews();
    } else {
        toastError('Failed to schedule interview');
    }
}

async function sendInterviewEmail(interviewId, type) {
    if (!confirm('Send ' + (type === 'invite' ? 'interview invite' : 'verdict update') + ' email to candidate?')) return;
    
    const res = await fetch('/api/interviews/' + interviewId + '/send-email', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ type: type })
    });
    
    if (res.ok) {
        toastSuccess('Email sent!');
    } else {
        const result = await res.json();
        toastError(result.error || 'Failed to send email');
    }
}

async function updateInterviewVerdict(interviewId, verdict) {
    const feedback = prompt('Add feedback (optional):', '');
    const res = await fetch('/api/interviews/' + interviewId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ verdict: verdict, feedback: feedback || '' })
    });
    if (res.ok) {
        toastSuccess('Verdict updated!');
        loadInterviews();
    } else {
        toastError('Failed to update verdict');
    }
}

// Schedule button handler
document.addEventListener('DOMContentLoaded', function() {
       const scheduleInterviewBtn = document.getElementById('scheduleInterviewBtn');
    if (scheduleInterviewBtn) scheduleInterviewBtn.onclick = scheduleInterview;
    const addExpenseBtn = document.getElementById('addExpenseBtn');
if (addExpenseBtn) addExpenseBtn.onclick = async function() {
    const formData = new FormData();
    formData.append('expense_date', document.getElementById('expDate').value);
    formData.append('category', document.getElementById('expCategory').value);
    formData.append('description', document.getElementById('expDesc').value);
    formData.append('amount', document.getElementById('expAmount').value);
    formData.append('paid_by', document.getElementById('expPaidBy').value);
    formData.append('vendor', document.getElementById('expVendor').value);
    
    const fileInput = document.getElementById('expFile');
    if (fileInput.files[0]) {
        formData.append('bill_file', fileInput.files[0]);
    }
    
    if (!formData.get('expense_date') || !formData.get('amount')) { toastError('Date and amount required'); return; }
    
    const res = await fetch('/api/expenses', {
        method: 'POST',
        body: formData
    });
    
    if (res.ok) {
        toastSuccess('Expense added!');
        document.getElementById('expDate').value = '';
        document.getElementById('expDesc').value = '';
        document.getElementById('expAmount').value = '';
        document.getElementById('expVendor').value = '';
        document.getElementById('expPaidBy').value = '';
        document.getElementById('expFile').value = '';
        loadExpenses();
    } else {
        toastError('Failed to add expense');
    }
};    
    // Onboard button
    const onboardBtn = document.getElementById('onboardBtn');
    if (onboardBtn) onboardBtn.onclick = async function() {
        const candidateVal = document.getElementById('onbCandidate').value;
        const candidateId = candidateVal.split(' - ')[0].trim();
        if (!candidateId) { toastError('Select a candidate'); return; }
        
        const reqId = document.getElementById('onbRequirementId').value.trim();
        const reqName = document.getElementById('onbRequirementId').value.includes(' - ') ? 
            document.getElementById('onbRequirementId').value.split(' - ')[1].trim() : '';
        
        const data = {
            candidate_id: parseInt(candidateId),
            client_name: document.getElementById('onbClient').value,
            doj: document.getElementById('onbDOJ').value,
            resource_owner: document.getElementById('onbOwner').value,
            work_location: document.getElementById('onbLocation').value,
            monthly_salary: parseFloat(document.getElementById('onbSalary').value) || 0,
            billing_rate: parseFloat(document.getElementById('onbBilling').value) || 0,
            business_model: document.getElementById('onbModel').value,
            requirement_id: reqId ? 'SIT-R-' + reqId : '',
            requirement_name: reqName,
            po_number: document.getElementById('onbPO').value
        };
        
        if (!data.client_name || !data.doj) { toastError('Client and DOJ required'); return; }
        
        const formData = new FormData();
        Object.keys(data).forEach(key => formData.append(key, data[key]));
        const docFiles = document.getElementById('onbDocuments').files;
        for (let i = 0; i < docFiles.length; i++) {
            formData.append('documents', docFiles[i]);
        }

        console.log('Files count:', document.getElementById('onbDocuments').files.length);
        
        const res = await fetch('/api/onboarded', { method: 'POST', body: formData });
        if (res.ok) {
            toastSuccess('Resource onboarded!');
            document.getElementById('onbCandidate').value = '';
            document.getElementById('onbClient').value = '';
            document.getElementById('onbDOJ').value = '';
            document.getElementById('onbSalary').value = '';
            document.getElementById('onbBilling').value = '';
            document.getElementById('onbOwner').value = '';
            document.getElementById('onbLocation').value = '';
            document.getElementById('onbPO').value = '';
            loadOnboarded();
        } else {
            toastError('Failed to onboard');
        }
    };
});

async function deleteJob(jobId) {
    if (!confirm('Delete this requirement?')) return;
    const res = await fetch('/api/jobs/' + jobId, { method: 'DELETE' });
    if (res.ok) { toastSuccess('Job deleted'); loadJobs(); }
    else { toastError('Failed to delete'); }
}

async function toggleJobActive(jobId) {
    const job = allJobs.find(j => j.id == jobId);
    const newStatus = (job.is_active === 1 || job.is_active === true) ? 0 : 1;
    const res = await fetch('/api/jobs/' + jobId + '/toggle-active', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ is_active: newStatus })
    });
    if (res.ok) {
        toastSuccess(newStatus ? 'Requirement reopened!' : 'Requirement closed!');
        loadJobs();
    } else {
        toastError('Failed to update');
    }
}

async function loadJobs() {
    const res = await fetch('/api/jobs');
    allJobs = await res.json();
    const container = document.getElementById('jobsList');
    if(!allJobs.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
    
    container.innerHTML = allJobs.map(j => {
    const requirementId = j.requirement_id || ('SIT-R-' + String(j.id).padStart(3,'0'));
    
    // Build info badges
    let badges = '';
        if (j.working_mode && j.working_mode !== 'Not Specified') {
        badges += `<span style="background:#E8F0FE;color:#1A73E8;padding:2px 10px;border-radius:12px;font-size:11px;margin-right:4px;font-weight:600;">${escapeHtml(j.working_mode)}${j.working_mode === 'Hybrid' && j.hybrid_days ? ' (' + j.hybrid_days + 'd)' : ''}</span>`;
    }
    if (j.business_model && j.business_model !== 'Not Specified') {
        badges += `<span style="background:#E8F0FE;color:#1A73E8;padding:2px 10px;border-radius:12px;font-size:11px;margin-right:4px;font-weight:600;">${escapeHtml(j.business_model)}</span>`;
    }
    if (j.years_of_experience) {
        badges += `<span style="background:#F1F3F4;color:#5F6368;padding:2px 10px;border-radius:12px;font-size:11px;margin-right:4px;font-weight:600;">${j.years_of_experience}+ Yrs</span>`;
    }
    if (j.budget && currentUser && currentUser.role === 'admin') {
        badges += `<span style="background:#E8F0FE;color:#1A73E8;padding:2px 10px;border-radius:12px;font-size:11px;margin-right:4px;font-weight:600;">💰 ${escapeHtml(j.budget)}</span>`;
    }
    if (j.max_salary) {
        badges += `<span style="background:#E8F0FE;color:#1A73E8;padding:2px 10px;border-radius:12px;font-size:11px;margin-right:4px;font-weight:600;">💵 Max: ${escapeHtml(j.max_salary)}</span>`;
    }
    if (j.headcount && j.headcount > 1) {
        badges += `<span style="background:#F1F3F4;color:#5F6368;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">👥 ${j.headcount}</span>`;
    }
    
    return `<div class="card" style="cursor:pointer;">
        <div onclick="viewCandidatesForRequirement('${escapeHtml(requirementId)}')" style="flex:1;">
            <h3>${escapeHtml(j.title)} <span style="font-size:12px;background:#1B2A4A;color:#fff;padding:2px 8px;border-radius:10px;">${escapeHtml(requirementId)}</span></h3>
            ${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}
            ${j.end_client ? `<p style="font-size:13px;">🎯 End Client: ${escapeHtml(j.end_client)}</p>` : ''}
            ${j.payroll_company ? `<p style="font-size:13px;">💼 Payroll: ${escapeHtml(j.payroll_company)}</p>` : ''}
            ${badges ? `<div style="margin:8px 0;">${badges}</div>` : ''}
            <small>📅 ${new Date(j.created_at).toLocaleDateString()}</small>
        </div>
        ${currentUser && (currentUser.role === 'admin' || currentUser.role === 'manager') ? `<button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); editJob(${j.id})" style="margin-top:8px;">✏️ Edit</button>` : ''} ${currentUser && currentUser.role === 'admin' ? `<button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteJob(${j.id})" style="margin-top:8px;">🗑️ Delete</button>` : ''} ${currentUser && (currentUser.role === 'admin' || currentUser.role === 'manager') ? `<button class="btn btn-sm" onclick="event.stopPropagation(); toggleJobActive(${j.id})" style="margin-top:8px;background:${(j.is_active === 1 || j.is_active === true) ? '#EF4444' : '#10B981'};">${j.is_active === 1 || j.is_active === true ? '🔒 Close' : '🔓 Reopen'}</button>` : ''}
        <button class="btn btn-sm" onclick="event.stopPropagation(); viewCandidatesForRequirement('${escapeHtml(requirementId)}')" style="margin-top:8px;">👥 View Candidates</button>
    </div>`;
}).join('');
    
    document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    document.getElementById('batchJobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
}
async function viewCandidatesForRequirement(requirementId) {
    // Normalize requirement ID - remove SIT-R- prefix and trim
    const normalizedReq = String(requirementId).replace('SIT-R-', '').trim();
    
    // Filter candidates by this requirement - check multiple fields and formats
    const matched = allCandidates.filter(c => {
        const proposed = String(c.proposed_requirement || '').replace('SIT-R-', '').trim();
        const matchedJd = String(c.matched_jd || '').replace('SIT-R-', '').trim();
        return proposed === normalizedReq || matchedJd === normalizedReq;
    });
    
    if (matched.length === 0) {
        toastInfo('No candidates linked to SIT-R-' + normalizedReq);
        return;
    }
    
    // Switch to candidates panel
    showPanel('candidates');
    
    // Display only matched candidates
    renderCandidates(matched);
    
    // Show count
    toastSuccess('Found ' + matched.length + ' candidate(s) for SIT-R-' + normalizedReq);
}
       
   async function loadCandidates() {
    try {
        const res = await fetch('/api/candidates');
        const data = await res.json();
        allCandidates = Array.isArray(data) ? data : [];
    } catch(e) {
        console.error('loadCandidates error:', e);
        allCandidates = [];
    }
    filterCandidates();
    // updatePipelineStats();  // ← REMOVED - function doesn't exist
    renderUploaderStats();
    document.getElementById('candidateSelect').innerHTML = '<option value="">-- Select Candidate --</option>' + allCandidates.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
  refreshDashboard();
}
// ============================================
// UPDATE DASHBOARD STATISTICS
// ============================================
function updateDashboardStats() {
    const candidates = allCandidates || [];
    const total = candidates.length;
    
    // Calculate average match score
    let totalScore = 0;
    let scoredCount = 0;
    candidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) {
            totalScore += score;
            scoredCount++;
        }
    });
    const avgScore = scoredCount > 0 ? Math.round(totalScore / scoredCount) : 0;
    
    // Count hired and rejected
    const hired = candidates.filter(c => c.employment_status === 'hired').length;
    const rejected = candidates.filter(c => c.employment_status === 'rejected').length;
    const pending = candidates.filter(c => 
        c.employment_status === 'new' || 
        c.employment_status === 'screening' || 
        c.employment_status === 'interview' ||
        c.employment_status === 'offer' ||
        !c.employment_status
    ).length;
    
    // Update SIMPLE stat cards (the ones that exist)
    const totalEl = document.getElementById('simple-total');
    const avgEl = document.getElementById('simple-avg');
    const hiredEl = document.getElementById('simple-hired');
    const rejectedEl = document.getElementById('simple-rejected');
    const pendingEl = document.getElementById('simple-pending');
    
    if (totalEl) totalEl.textContent = total;
    if (avgEl) avgEl.textContent = avgScore + '%';
    if (hiredEl) hiredEl.textContent = hired;
    if (rejectedEl) rejectedEl.textContent = rejected;
    if (pendingEl) pendingEl.textContent = pending;
}

// ============================================
// RENDER MATCH SCORE CHART
// ============================================
function renderChart() {
    const chart = document.getElementById('score-chart');
    if (!chart) return;
    
    const candidates = allCandidates || [];
    const scores = [];
    
    // Collect all match scores
    candidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) scores.push(score);
    });
    
    if (scores.length === 0) {
        chart.innerHTML = '<p style="text-align: center; color: #999; width: 100%;">No data to display</p>';
        return;
    }
    
    // Group scores into ranges
    const ranges = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    };
    
    scores.forEach(score => {
        if (score <= 20) ranges['0-20']++;
        else if (score <= 40) ranges['21-40']++;
        else if (score <= 60) ranges['41-60']++;
        else if (score <= 80) ranges['61-80']++;
        else ranges['81-100']++;
    });
    
    const max = Math.max(...Object.values(ranges), 1);
    const colors = ['#f44336', '#ff9800', '#ffc107', '#4caf50', '#2196f3'];
    const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
    
    let html = '';
    let index = 0;
    for (const [range, count] of Object.entries(ranges)) {
        const height = Math.max((count / max) * 100, 5); // Minimum 5% height for visibility
        const color = colors[index];
        html += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                <div class="bar" style="width: 100%; max-width: 40px; border-radius: 4px 4px 0 0; height: ${height}%; background: ${color}; transition: height 0.5s ease; min-height: 5px;"></div>
                <span class="bar-label" style="font-size: 11px; color: #666;">${labels[index]}</span>
                <span class="bar-label" style="font-size: 10px; font-weight: 600; color: #333;">${count}</span>
            </div>
        `;
        index++;
    }
    
    chart.innerHTML = html;
}

// ============================================
// REFRESH DASHBOARD (called from page load)
// ============================================
function refreshDashboard() {
    updateDashboardStats();
    renderChart();
}
    
    // ============================================
// FILTER CANDIDATES - ENHANCED VERSION
// ============================================
function filterCandidates() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const scoreFilter = document.getElementById('scoreFilter').value;
    const uploaderFilter = document.getElementById('uploadedByFilter').value.toLowerCase();
    const sortBy = document.getElementById('sortBy').value;
    
    let filtered = Array.isArray(allCandidates) ? allCandidates : [];
    
    // 1. Search filter - name, email, phone, skills
    if (searchTerm) {
        filtered = filtered.filter(c => {
            const name = ((c.first_name || '') + ' ' + (c.last_name || '')).toLowerCase().trim();
            const email = (c.email || '').toLowerCase();
            const phone = (c.phone || '').toLowerCase();
            let skills = '';
            if (c.core_skills) {
                try {
                    const parsedSkills = JSON.parse(c.core_skills);
                    skills = parsedSkills.map(s => (s.skill || '').toLowerCase()).join(' ');
                } catch(e) {
                    skills = '';
                }
            }
            return name.includes(searchTerm) || 
                   email.includes(searchTerm) || 
                   phone.includes(searchTerm) || 
                   skills.includes(searchTerm);
        });
    }
    
    // 2. Status filter
    if (statusFilter !== 'all') {
        filtered = filtered.filter(c => (c.stage || c.employment_status || 'new') === statusFilter);
    }
    
    // 3. Score filter
    if (scoreFilter === 'high') {
        filtered = filtered.filter(c => (c.match_score || 0) >= 70);
    } else if (scoreFilter === 'medium') {
        filtered = filtered.filter(c => (c.match_score || 0) >= 40 && (c.match_score || 0) < 70);
    } else if (scoreFilter === 'low') {
        filtered = filtered.filter(c => (c.match_score || 0) < 40);
    }
    
    // 4. Uploader filter
    if (uploaderFilter) {
    filtered = filtered.filter(c => 
        (c.uploaded_by || c.uploaded_by_name || 'ShahnaIT').toLowerCase().includes(uploaderFilter.toLowerCase())
    );
}
    
    // 5. Sorting
    if (sortBy === 'score') {
        filtered.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
    } else if (sortBy === 'name') {
        filtered.sort((a, b) => ((a.first_name || '') + ' ' + (a.last_name || '')).localeCompare((b.first_name || '') + ' ' + (b.last_name || '')));
    } else if (sortBy === 'date') {
        filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortBy === 'status') {
        filtered.sort((a, b) => (a.stage || a.employment_status || '').localeCompare(b.stage || b.employment_status || ''));
    } else if (sortBy === 'uploader') {
        filtered.sort((a, b) => (a.uploaded_by || 'ShahnaIT').localeCompare(b.uploaded_by || 'ShahnaIT'));
    }
    
    // 6. Render the filtered candidates
    renderCandidates(filtered);
    
    // 7. Update dashboard stats based on filtered results
    updateFilteredStats(filtered);
}
// ============================================
// UPDATE STATS BASED ON FILTERED RESULTS
// ============================================
function updateFilteredStats(filteredCandidates) {
    const total = filteredCandidates.length;
    
    // Calculate average match score for filtered results
    let totalScore = 0;
    let scoredCount = 0;
    filteredCandidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) {
            totalScore += score;
            scoredCount++;
        }
    });
    const avgScore = scoredCount > 0 ? Math.round(totalScore / scoredCount) : 0;
    
    // Count shortlisted in filtered results
    const shortlisted = filteredCandidates.filter(c => 
        c.employment_status === 'hired' || 
        c.employment_status === 'offer' || 
        c.employment_status === 'shortlisted'
    ).length;
    
    // Count pending review in filtered results
    const pendingReview = filteredCandidates.filter(c => 
        c.employment_status === 'new' || 
        c.employment_status === 'screening' || 
        c.employment_status === 'interview' ||
        !c.employment_status
    ).length;
    
    // Update the SIMPLE stat cards (not the old ones)
    const totalEl = document.getElementById('simple-total');
    const avgEl = document.getElementById('simple-avg');
    const hiredEl = document.getElementById('simple-hired');
    const rejectedEl = document.getElementById('simple-rejected');
    const pendingEl = document.getElementById('simple-pending');
    
    if (totalEl) totalEl.textContent = total;
    if (avgEl) avgEl.textContent = avgScore + '%';
    if (hiredEl) hiredEl.textContent = shortlisted;
    if (pendingEl) pendingEl.textContent = pendingReview;
    if (rejectedEl) rejectedEl.textContent = filteredCandidates.filter(c => c.employment_status === 'rejected').length;
    
    // Re-render the chart with filtered data
    renderFilteredChart(filteredCandidates);
}
// ============================================
// RENDER CHART WITH FILTERED DATA
// ============================================
function renderFilteredChart(filteredCandidates) {
    const chart = document.getElementById('score-chart');
    if (!chart) return;
    
    const scores = [];
    
    // Collect all match scores from filtered candidates
    filteredCandidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) scores.push(score);
    });
    
    if (scores.length === 0) {
        chart.innerHTML = '<p style="text-align: center; color: #999; width: 100%;">No data to display</p>';
        return;
    }
    
    // Group scores into ranges
    const ranges = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    };
    
    scores.forEach(score => {
        if (score <= 20) ranges['0-20']++;
        else if (score <= 40) ranges['21-40']++;
        else if (score <= 60) ranges['41-60']++;
        else if (score <= 80) ranges['61-80']++;
        else ranges['81-100']++;
    });
    
    const max = Math.max(...Object.values(ranges), 1);
    const colors = ['#f44336', '#ff9800', '#ffc107', '#4caf50', '#2196f3'];
    const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
    
    let html = '';
    let index = 0;
    for (const [range, count] of Object.entries(ranges)) {
        const height = Math.max((count / max) * 100, 5);
        const color = colors[index];
        html += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                <div class="bar" style="width: 100%; max-width: 40px; border-radius: 4px 4px 0 0; height: ${height}%; background: ${color}; transition: height 0.5s ease; min-height: 5px;"></div>
                <span class="bar-label" style="font-size: 11px; color: #666;">${labels[index]}</span>
                <span class="bar-label" style="font-size: 10px; font-weight: 600; color: #333;">${count}</span>
            </div>
        `;
        index++;
    }
    
    chart.innerHTML = html;
}
    
   // ============================================
// RENDER CANDIDATE CARDS - IMPROVED VERSION
// ============================================
function renderCandidates(candidates) {
    const container = document.getElementById('candidatesList');
    if(!candidates.length) { 
        container.innerHTML = '<div class="card no-click" style="text-align: center; padding: 40px; color: #666;">🔍 No candidates found</div>'; 
        return; 
    }
    
    container.innerHTML = candidates.map(c => {
        const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
        let skills = [];
try {
    if (c.core_skills) {
        skills = typeof c.core_skills === 'string' ? JSON.parse(c.core_skills) : c.core_skills;
        // Handle double-encoded JSON
        if (typeof skills === 'string') {
            try { skills = JSON.parse(skills); } catch(e2) { skills = []; }
        }
    }
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];
// Flatten if skills contain objects
skills = skills.map(s => {
    if (typeof s === 'object' && s !== null) return s.skill || s.name || '';
    return String(s);
}).filter(Boolean);
        const matchScore = c.match_score || 0;
        const matchClass = matchScore >= 70 ? 'match-high' : (matchScore >= 40 ? 'match-medium' : 'match-low');
        const status = c.stage || c.employment_status || 'new';
        
        // Status colors
        const statusColors = {
            'new': '#2196F3',
            'screening': '#FF9800',
            'interview': '#FF5722',
            'offer': '#9C27B0',
            'hired': '#4CAF50',
            'rejected': '#F44336'
        };
        const statusLabels = {
            'new': '🟢 New',
            'screening': '🔵 Screening',
            'interview': '🟠 Interview',
            'offer': '🟣 Offer',
            'hired': '✅ Hired',
            'rejected': '❌ Rejected'
        };
        const uploadedBy = c.uploaded_by || 'ShahnaIT';
        
        return `
        <div class="candidate-card" data-id="${c.id}" onclick="viewCandidate(${c.id})">
            <div class="card-header">
                <div class="candidate-avatar">
                    <span class="avatar-text">${escapeHtml(name.charAt(0) || '?')}</span>
                    ${matchScore > 0 ? `<div class="score-badge" style="background: ${matchScore >= 70 ? '#4caf50' : (matchScore >= 40 ? '#ff9800' : '#f44336')}">${matchScore}%</div>` : ''}
                </div>
                <div class="candidate-title">
                    <h3 class="candidate-name">👤 ${escapeHtml(name)}</h3>
                    <span class="candidate-email">${c.email ? '📧 ' + escapeHtml(c.email) : ''}</span>
                </div>
                <button class="btn-expand" onclick="event.stopPropagation(); toggleCandidateDetails(${c.id})">
                    <i class="fas fa-chevron-down"></i>
                </button>
            </div>
            
            <div class="card-body">
                <div class="candidate-skills">
                    ${skills.length > 0 ? skills.slice(0,5).map(s => 
    `<span class="skill-tag">${escapeHtml(typeof s === 'object' ? (s.skill || s.name || '') : s)}</span>`
                    ).join('') : '<span class="no-skills">No skills listed</span>'}
                    ${skills.length > 5 ? `<span class="skill-tag more">+${skills.length - 5}</span>` : ''}
                </div>
                
                <div class="candidate-meta">
                    <span class="meta-item">
                        <i class="fas fa-phone"></i> ${c.phone || 'N/A'}
                    </span>
                    <span class="meta-item">
                        <i class="fas fa-calendar"></i> ${c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}
                    </span>
                    <span class="status-badge status-${status}" style="background: ${statusColors[status]}22; color: ${statusColors[status]};">
                        ${statusLabels[status] || status}
                    </span>
                    <span class="meta-item" style="font-size: 11px; color: #999;">
                        👤 ${escapeHtml(uploadedBy)}
                    </span>
                </div>
                
                <div class="card-actions">
                    <button class="btn-primary" onclick="event.stopPropagation(); viewCandidate(${c.id})">
    <i class="fas fa-eye"></i> View Details
</button>
${!c.proposed_date ? `<button class="btn-secondary" onclick="event.stopPropagation(); markProposed(${c.id})" style="background:#C9A96E;">📤 Propose</button>` : `<span style="font-size:11px;color:#10B981;margin-left:4px;">✅ ${escapeHtml(c.proposed_date||'')}</span>`}
                    </button>
                    <button class="btn-secondary" onclick="event.stopPropagation(); exportPDF(${c.id}, event)">
                        <i class="fas fa-file-pdf"></i> Export PDF
                    </button>
                    ${(currentUser && (currentUser.role === 'admin' || currentUser.full_name === 'Siraj' || currentUser.full_name === 'Ibaad')) ? `<button class="btn-danger" onclick="event.stopPropagation(); deleteCandidate(${c.id})"><i class="fas fa-trash"></i></button>` : ''}
                </div>
            </div>
            
            <!-- Expanded Details -->
            <div class="card-details" id="details-${c.id}" style="display: none;">
                <div class="details-section">
                    <h4>📊 AI Analysis</h4>
                    <p>${c.detailed_analysis ? 'Analysis available' : 'No analysis available'}</p>
                </div>
                <div class="details-section">
                    <h4>📝 Notes</h4>
                    <div class="notes-container" id="notes-${c.id}">
                        <p style="color: #999; font-style: italic;">Loading notes...</p>
                    </div>
                    <input type="text" class="note-input" placeholder="Add a note..." 
                           onkeypress="if(event.key==='Enter') addNote(${c.id}, this.value)">
                </div>
            </div>
        </div>`;
    }).join('');
}
// ============================================
// TOGGLE CANDIDATE DETAILS
// ============================================
function toggleCandidateDetails(id) {
    const details = document.getElementById(`details-${id}`);
    if (!details) return;
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        // Load notes when expanded
        loadNotes(id);
    } else {
        details.style.display = 'none';
    }
}

// ============================================
// LOAD NOTES FOR CANDIDATE
// ============================================
async function loadNotes(candidateId) {
    const container = document.getElementById(`notes-${candidateId}`);
    if (!container) return;
    
    try {
        const res = await fetch(`/api/candidates/${candidateId}/notes`);
        const notes = await res.json();
        
        if (notes.length === 0) {
            container.innerHTML = '<p style="color: #999; font-style: italic; margin: 5px 0;">No notes yet. Add one above.</p>';
            return;
        }
        
        let html = '';
        notes.forEach(note => {
            const date = new Date(note.created_at).toLocaleString();
            html += `
                <div style="background: #F9F6F0; padding: 8px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #1A4D4A;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1; font-size: 13px;">${escapeHtml(note.note_text)}</div>
                        <button class="btn" style="background: #B22222; padding: 2px 8px; font-size: 10px; margin-left: 8px; border: none; border-radius: 4px; color: white; cursor: pointer;" onclick="deleteNote(${note.id}, ${candidateId})">✕</button>
                    </div>
                    <small style="color: #666; font-size: 10px;">📅 ${date}</small>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch(e) {
        container.innerHTML = '<p style="color: #B22222;">Failed to load notes</p>';
    }
}

// ============================================
// ADD NOTE
// ============================================
async function addNote(candidateId, inputElement) {
    const noteText = inputElement.trim();
    if (!noteText) { toastWarning('Please enter a note'); return; }
    
    try {
        const res = await fetch(`/api/candidates/${candidateId}/notes`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ note_text: noteText })
        });
        
        if (res.ok) {
            // Clear input
            const inputField = document.querySelector(`#details-${candidateId} .note-input`);
            if (inputField) inputField.value = '';
            loadNotes(candidateId);
            toastSuccess('Note added!');
        } else {
            toastError('Failed to add note');
        }
    } catch(e) {
        toastError('Error adding note');
    }
}

// ============================================
// DELETE NOTE
// ============================================
async function deleteNote(noteId, candidateId) {
    if (!confirm('Delete this note?')) return;
    
    try {
        const res = await fetch(`/api/candidates/notes/${noteId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            loadNotes(candidateId);
            toastSuccess('Note deleted');
        } else {
            toastError('Failed to delete note');
        }
    } catch(e) {
        toastError('Error deleting note');
    }
}

// ============================================
// DELETE CANDIDATE
// ============================================
async function markProposed(candidateId) {
    if (!confirm('Mark this candidate as proposed?')) return;
    const date = new Date().toISOString().split('T')[0];
    const res = await fetch('/api/candidates/' + candidateId + '/propose', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ proposed_date: date })
    });
    if (res.ok) {
        toastSuccess('Marked as proposed!');
        loadCandidates();
    } else {
        toastError('Failed to mark');
    }
}

async function deleteCandidate(candidateId) {
    if (!confirm('Delete this candidate?')) return;
    
    try {
        const res = await fetch(`/api/candidates/${candidateId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            toastSuccess('Candidate deleted');
            loadCandidates();
        } else {
            toastError('Failed to delete candidate');
        }
    } catch(e) {
        toastError('Error deleting candidate');
    }
}
    
   // ============================================
// EVENT LISTENERS FOR FILTERS
// ============================================
// Search input - real-time filtering
document.getElementById('searchBox').addEventListener('input', filterCandidates);

// Status filter
document.getElementById('statusFilter').addEventListener('change', filterCandidates);

// Score filter
document.getElementById('scoreFilter').addEventListener('change', filterCandidates);

// Uploader filter
document.getElementById('uploadedByFilter').addEventListener('input', filterCandidates);

// Sort by
document.getElementById('sortBy').addEventListener('change', filterCandidates);

// Clear all filters
document.getElementById('clearFiltersBtn').addEventListener('click', function() {
    document.getElementById('searchBox').value = '';
    document.getElementById('statusFilter').value = 'all';
    document.getElementById('scoreFilter').value = 'all';
    document.getElementById('uploadedByFilter').value = '';
    document.getElementById('sortBy').value = 'score';
    filterCandidates();
    
    // Show success message
    toastSuccess('Filters cleared!');
});
    
   // Edit Job
    window.editJob = async function(id) {
        const job = allJobs.find(j => j.id == id);
        const docRes = await fetch(`/api/jobs/${id}/documents`);
        const documents = await docRes.json();
        let docsHtml = '';
        if (documents.length > 0) {
            docsHtml = '<h4>Attached Documents</h4><div class="file-list">';
            documents.forEach(doc => { docsHtml += `<div class="file-list-item">📄 ${escapeHtml(doc.original_filename)} <span class="remove-file" onclick="deleteJobDocument(${doc.id}, ${id})">✕ Remove</span></div>`; });
            docsHtml += '</div>';
        }
        
        const workingModeOptions = ['Not Specified', 'Remote', 'Hybrid', 'Onsite']
            .map(m => `<option value="${m}" ${(job.working_mode || 'Not Specified') === m ? 'selected' : ''}>${m}</option>`).join('');
        const businessModelOptions = ['Not Specified', 'C2C', 'C2H', 'Permanent', 'Contract']
            .map(m => `<option value="${m}" ${(job.business_model || 'Not Specified') === m ? 'selected' : ''}>${m}</option>`).join('');
        
        document.getElementById('editJobModalBody').innerHTML = `<form id="editJobForm">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group"><label>Job Title</label><input type="text" id="editJobTitle" class="form-input" value="${escapeHtml(job.title || '')}"></div>
                <div class="form-group"><label>Company</label><input type="text" id="editJobCompany" class="form-input" value="${escapeHtml(job.company || '')}"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group">
                    <label>Working Mode</label>
                    <select id="editJobWorkingMode" class="form-input">${workingModeOptions}</select>
                </div>
                <div class="form-group">
                    <label>Business Model</label>
                    <select id="editJobBusinessModel" class="form-input">${businessModelOptions}</select>
                </div>
            </div>
            <div class="form-group" id="editHybridDaysGroup" style="display:${(job.working_mode === 'Hybrid') ? 'block' : 'none'};">
                <label>Hybrid Days (per week)</label>
                <input type="number" id="editJobHybridDays" class="form-input" value="${job.hybrid_days || 0}" min="0" max="7">
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group"><label>Payroll Company</label><input type="text" id="editJobPayroll" class="form-input" value="${escapeHtml(job.payroll_company || '')}"></div>
                <div class="form-group"><label>End Client</label><input type="text" id="editJobEndClient" class="form-input" value="${escapeHtml(job.end_client || '')}"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                <div class="form-group"><label>Years of Experience</label><input type="number" id="editJobExperience" class="form-input" value="${job.years_of_experience || 0}" min="0"></div>
               ${currentUser && currentUser.role === 'admin' ? `<div class="form-group"><label>Budget</label><input type="text" id="editJobBudget" class="form-input" value="${escapeHtml(job.budget || '')}"></div>` : ''}
<div class="form-group"><label>Max Salary</label><input type="text" id="editJobMaxSalary" class="form-input" value="${escapeHtml(job.max_salary || '')}"></div>
<div class="form-group"><label>Headcount</label><input type="number" id="editJobHeadcount" class="form-input" value="${job.headcount || 1}" min="1"></div>
            <div class="form-group"><label>Roles & Responsibilities</label><textarea id="editJobRoles" class="form-input" rows="4">${escapeHtml(job.roles_responsibilities || '')}</textarea></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group"><label>Qualifications</label><textarea id="editJobQualifications" class="form-input" rows="3">${escapeHtml(job.qualifications || '')}</textarea></div>
                <div class="form-group"><label>Certifications Required</label><input type="text" id="editJobCertifications" class="form-input" value="${escapeHtml(job.certifications_required || '')}"></div>
            </div>
            <div class="form-group"><label>Required Skills</label><input type="text" id="editJobSkills" class="form-input" value="${escapeHtml(job.required_skills || '')}"></div>
            <div class="form-group"><label>Description</label><textarea id="editJobDesc" class="form-input" rows="5">${escapeHtml(job.description || '')}</textarea></div>
            <h4>Attach Document</h4><input type="file" id="jobDocFile"><button type="button" id="uploadJobDocBtn" class="btn btn-secondary">Upload</button><div id="jobDocUploadStatus"></div>${docsHtml}
            <div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditJobModal()">Cancel</button></div>
        </form>`;
        
        document.getElementById('editJobModal').style.display = 'block';
        
        // Show/hide hybrid days
        const editWorkingMode = document.getElementById('editJobWorkingMode');
        const editHybridGroup = document.getElementById('editHybridDaysGroup');
        if (editWorkingMode && editHybridGroup) {
            editWorkingMode.addEventListener('change', function() {
                editHybridGroup.style.display = this.value === 'Hybrid' ? 'block' : 'none';
            });
        }
        
        const uploadJobDocBtn = document.getElementById('uploadJobDocBtn');
        if (uploadJobDocBtn) uploadJobDocBtn.onclick = async function() {
            const file = document.getElementById('jobDocFile').files[0];
            if (!file) return;
            const fd = new FormData(); fd.append('document', file); fd.append('job_id', id);
            document.getElementById('jobDocUploadStatus').innerHTML = '<div class="spinner"></div>';
            const res = await fetch('/api/jobs/upload-document', { method: 'POST', body: fd });
            if (res.ok) { toastSuccess('Uploaded!'); editJob(id); }
            document.getElementById('jobDocUploadStatus').innerHTML = '';
        };
        
        document.getElementById('editJobForm').onsubmit = async (e) => {
    e.preventDefault();
    const data = {
        title: document.getElementById('editJobTitle').value,
        company: document.getElementById('editJobCompany').value,
        working_mode: document.getElementById('editJobWorkingMode').value,
        hybrid_days: parseInt(document.getElementById('editJobHybridDays').value) || 0,
        office_location: document.getElementById('editJobOfficeLocation') ? document.getElementById('editJobOfficeLocation').value : '',
        business_model: document.getElementById('editJobBusinessModel').value,
        payroll_company: document.getElementById('editJobPayroll').value,
        end_client: document.getElementById('editJobEndClient').value,
        years_of_experience: parseInt(document.getElementById('editJobExperience').value) || 0,
        budget: document.getElementById('editJobBudget') ? document.getElementById('editJobBudget').value : '',
        max_salary: document.getElementById('editJobMaxSalary') ? document.getElementById('editJobMaxSalary').value : '',
        headcount: parseInt(document.getElementById('editJobHeadcount').value) || 1,
        roles_responsibilities: document.getElementById('editJobRoles').value,
        qualifications: document.getElementById('editJobQualifications').value,
        certifications_required: document.getElementById('editJobCertifications').value,
        required_skills: document.getElementById('editJobSkills').value,
        description: document.getElementById('editJobDesc').value
    };
    const res = await fetch(`/api/jobs/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
    if (res.ok) { toastSuccess('Job updated!'); closeEditJobModal(); loadJobs(); }
     };
  };  

    
    window.deleteJobDocument = async function(docId, jobId) {
        if (confirm('Delete?')) { await fetch(`/api/jobs/documents/${docId}`, { method: 'DELETE' }); editJob(jobId); }
    };
    function closeEditJobModal() { document.getElementById('editJobModal').style.display = 'none'; }
    window.closeEditJobModal = closeEditJobModal;
    
   window.previewDocument = async function(docId) {
    try {
        const res = await fetch(`/api/documents/${docId}/preview`);
        const data = await res.json();

        if (data.error) {
            toastError(data.error);
            return;
        }

        if (data.type === 'image') {
            document.getElementById('previewBody').innerHTML = `
                <img src="data:image/png;base64,${data.content}" style="max-width:100%; border-radius: 8px;">
                <div style="margin-top: 15px; text-align: center;">
                    <button onclick="copyPreviewText()" style="background: #C9A96E; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        📋 Copy Image Description
                    </button>
                </div>
            `;
        } else {
            document.getElementById('previewBody').innerHTML = `
                <div style="white-space:pre-wrap; background: #f9f6f0; padding: 15px; border-radius: 8px; max-height: 500px; overflow-y: auto; user-select: text; cursor: text; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6; border: 1px solid #e0e0e0;">
                    ${escapeHtml(data.content)}
                </div>
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                    <button onclick="copyPreviewText()" style="background: #C9A96E; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        📋 Copy All Text
                    </button>
                    <button onclick="window.print()" style="background: #1A4D4A; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        🖨️ Print
                    </button>
                </div>
            `;
        }
        document.getElementById('previewModal').style.display = 'block';
    } catch (e) {
        toastError('Error loading preview');
        console.error('Preview error:', e);
    }
};
// ============================================
// VIEW ORIGINAL RESUME (Opens in new tab)
// ============================================
function viewOriginalResume(candidateId) {
    const candidate = allCandidates.find(c => c.id == candidateId);
    const filename = candidate ? (candidate.resume_original_filename || '') : '';
    const url = `/api/candidates/${candidateId}/view-resume`;
    
    if (filename.endsWith('.docx') || filename.endsWith('.doc')) {
        const fullUrl = window.location.origin + url;
        window.open(`https://docs.google.com/viewer?url=${encodeURIComponent(fullUrl)}`, '_blank');
    } else {
        window.open(url, '_blank');
    }
}

// ============================================
// COPY RESUME TEXT TO CLIPBOARD
// ============================================
async function copyResumeText(candidateId) {
    try {
        const container = document.getElementById(`resume-text-${candidateId}`);
        if (!container) {
            toastError('Resume text not found');
            return;
        }
        
        const text = container.textContent;
        
        // Check if there's actual text
        if (!text || text.trim() === '' || text.includes('No resume text available')) {
            toastWarning('No resume text to copy');
            return;
        }
        
        // Try using the Clipboard API
        try {
            await navigator.clipboard.writeText(text);
            toastSuccess('Resume text copied to clipboard!');
            return;
        } catch (e) {
            // Fallback: use the old method
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            toastSuccess('Resume text copied to clipboard!');
        }
    } catch (e) {
        toastError('Failed to copy text');
        console.error('Copy error:', e);
    }
}

// ============================================
// COPY PREVIEW TEXT
// ============================================
function copyPreviewText() {
    const previewBody = document.getElementById('previewBody');
    if (!previewBody) {
        toastError('Preview not found');
        return;
    }
    
    const textDiv = previewBody.querySelector('div');
    if (!textDiv) {
        toastError('No text to copy');
        return;
    }
    
    const text = textDiv.textContent;
    
    // Try using the Clipboard API
    navigator.clipboard.writeText(text).then(() => {
        toastSuccess('Preview text copied!');
    }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        toastSuccess('Preview text copied!');
    });
}
    function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }
    window.closeEditModal = closeEditModal;
    function closeDocModal() { document.getElementById('docModal').style.display = 'none'; }
    window.closeDocModal = closeDocModal;
    
    window.openEditModal = async function(id) {
        const c = allCandidates.find(c => c.id == id);
        const skillsStr = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill).join(', ') : '';
        const certsStr = c.certifications ? JSON.parse(c.certifications).join(', ') : '';
        document.getElementById('editModalBody').innerHTML = `<form id="editForm"><div class="flex"><div class="flex-1"><label>First Name</label><input type="text" id="editFirst" value="${escapeHtml(c.first_name||'')}"></div><div class="flex-1"><label>Middle</label><input type="text" id="editMiddle" value="${escapeHtml(c.middle_name||'')}"></div><div class="flex-1"><label>Last</label><input type="text" id="editLast" value="${escapeHtml(c.last_name||'')}"></div></div><div class="flex"><div class="flex-1"><label>Email</label><input type="email" id="editEmail" value="${escapeHtml(c.email||'')}"></div><div class="flex-1"><label>Phone</label><input type="text" id="editPhone" value="${escapeHtml(c.phone||'')}"></div></div><div class="flex"><div class="flex-1"><label>Current CTC</label><input type="text" id="editCurrentCTC" value="${escapeHtml(c.current_ctc||'')}"></div><div class="flex-1"><label>Expected CTC</label><input type="text" id="editExpectedCTC" value="${escapeHtml(c.expected_ctc||'')}"></div></div><label>Address</label><input type="text" id="editAddress" value="${escapeHtml(c.address||'')}"><label>LinkedIn</label><input type="text" id="editLinkedin" value="${escapeHtml(c.linkedin||'')}"><label>Current Role</label><input type="text" id="editRole" value="${escapeHtml(c.current_role||'')}"><div class="flex"><div class="flex-1"><label>Status</label><select id="editStatus"><option value="working" ${c.employment_status==='working'?'selected':''}>Working</option><option value="bench" ${c.employment_status==='bench'?'selected':''}>Bench</option><option value="notice_period" ${c.employment_status==='notice_period'?'selected':''}>Notice</option></select></div><div class="flex-1"><label>Notice Days</label><input type="number" id="editNoticeDays" value="${c.notice_period_days||0}"></div></div><label>Education</label><textarea id="editEducation" rows="2">${escapeHtml(c.education||'')}</textarea><label>📝 Notes</label><textarea id="editNotes" rows="3" style="background: #FFF8E1; border-left: 4px solid #C9A96E; padding: 10px;">${escapeHtml(c.notes||'')}</textarea><label>Skills (comma)</label><input type="text" id="editSkills" value="${escapeHtml(skillsStr)}"><label>Certifications (comma)</label><input type="text" id="editCerts" value="${escapeHtml(certsStr)}"><div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button></div></form>`;
        document.getElementById('editModal').style.display = 'block';
        document.getElementById('editForm').onsubmit = async (e) => {
            e.preventDefault();
            const skillsArray = document.getElementById('editSkills').value.split(',').map(s => ({skill: s.trim(), years_of_experience: 0})).filter(s => s.skill);
            const certsArray = document.getElementById('editCerts').value.split(',').map(c => c.trim()).filter(c => c);
            const data = {
                first_name: document.getElementById('editFirst').value, middle_name: document.getElementById('editMiddle').value, last_name: document.getElementById('editLast').value,
                email: document.getElementById('editEmail').value, phone: document.getElementById('editPhone').value,
                current_ctc: document.getElementById('editCurrentCTC').value, expected_ctc: document.getElementById('editExpectedCTC').value,
                address: document.getElementById('editAddress').value, linkedin: document.getElementById('editLinkedin').value,
                current_role: document.getElementById('editRole').value, employment_status: document.getElementById('editStatus').value,
                notice_period_days: parseInt(document.getElementById('editNoticeDays').value) || 0, education: document.getElementById('editEducation').value,
                notes: document.getElementById('editNotes').value, core_skills: JSON.stringify(skillsArray), certifications: JSON.stringify(certsArray)
            };
            const res = await fetch(`/api/candidates/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
           if (res.ok) { toastSuccess('Updated!'); closeEditModal(); loadCandidates(); viewCandidate(id); }
        };
    };
    
    // Document upload - with null checks
window.openDocModal = function(id) { 
    currentCandidateId = id; 
    const docModal = document.getElementById('docModal');
    if (docModal) docModal.style.display = 'block'; 
};

const uploadDocBtn = document.getElementById('uploadDocBtn');
if (uploadDocBtn) {
    if (uploadDocBtn) uploadDocBtn.onclick = async function() {
        const docFile = document.getElementById('docFile');
        if (!docFile) return;
        const file = docFile.files[0];
        if (!file || !currentCandidateId) return;
        const fd = new FormData(); 
        fd.append('document', file); 
        fd.append('candidate_id', currentCandidateId);
        const docUploadStatus = document.getElementById('docUploadStatus');
        if (docUploadStatus) docUploadStatus.innerHTML = '<div class="spinner"></div>';
        const res = await fetch('/api/candidates/upload-document', { method: 'POST', body: fd });
        if (res.ok) { 
            toastSuccess('Uploaded!'); 
            const closeDocModal = window.closeDocModal;
            if (closeDocModal) closeDocModal(); 
            viewCandidate(currentCandidateId); 
        }
        if (docUploadStatus) docUploadStatus.innerHTML = '';
    };
}
    
    const exportBtn = document.getElementById('exportBtn');
if (exportBtn) exportBtn.onclick = () => window.location.href = '/api/export-candidates';
    
    const parseBtn = document.getElementById('parseBtn');
if (parseBtn) parseBtn.onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if(!file) return;
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
        const result = await res.json();
        if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
        div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name||'')} ${escapeHtml(result.last_name||'')}</p><p><strong>Email:</strong> ${escapeHtml(result.email||'')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone||'')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(typeof s === 'object' ? (s.skill || s.name || '') : s)}</span>`).join('') : 'None'}</p><button id="saveBtn">💾 Save</button></div>`;
                             const saveBtn = document.getElementById('saveBtn'); if (saveBtn) saveBtn.onclick = async function() {
            // Check for duplicates first
            const dupRes = await fetch('/api/candidates/check-duplicate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: result.email, phone: result.phone })
            });
            const dupData = await dupRes.json();
            
            if (dupData.duplicate) {
                const dupNames = dupData.matches.map(m => `${m.first_name} ${m.last_name} (${m.email || m.phone})`).join(', ');
                const skip = confirm(`⚠️ Possible duplicate found!

Existing candidate(s): ${dupNames}

Matched by: ${dupData.matched_by}

Click OK to save anyway, Cancel to skip.`);
                if (!skip) { toastInfo('Skipped duplicate'); return; }
            }
            
            // Ask for uploader name
                        // Ask for uploader name
            const uploaded_by = document.getElementById('uploaderSelect').value;
if (!uploaded_by) {
    toastError('Please select uploader first');
    return;
}
result.uploaded_by = uploaded_by;
            
            const saveRes = await fetch('/api/candidates', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify(result) 
            });
            if(saveRes.ok) { 
                toastSuccess('Saved! Resume auto-attached!'); 
                div.innerHTML = ''; 
                document.getElementById('resumeFile').value = ''; 
                loadCandidates(); 
                showPanel('candidates'); 
            }
            else alert('Error');
        };
    };
    
   const parseJDBtn = document.getElementById('parseJDBtn');
if (parseJDBtn) parseJDBtn.onclick = async function() {
    const fileInput = document.getElementById('jdFileInput');
    const file = fileInput.files[0];
    if (!file) { toastError('Please select a file'); return; }
    
    const status = document.getElementById('jdParseStatus');
    status.innerHTML = '<div class="spinner"></div> Parsing...';
    
    const fd = new FormData();
    fd.append('file', file);
    
    try {
        const res = await fetch('/api/jobs/parse-jd', { method: 'POST', body: fd });
        const result = await res.json();
        
        if (result.success && result.parsed) {
            const p = result.parsed;
            document.getElementById('jobTitle').value = p.title || '';
            document.getElementById('jobRoles').value = p.roles_responsibilities || '';
            document.getElementById('jobQualifications').value = p.qualifications || '';
            document.getElementById('jobSkills').value = (p.required_skills || []).join(', ');
            document.getElementById('jobDesc').value = result.text || '';
            status.innerHTML = '✅ JD parsed successfully!';
            toastSuccess('JD parsed!');
        } else {
            status.innerHTML = '❌ ' + (result.error || 'Parse failed');
        }
    } catch(e) {
        status.innerHTML = '❌ Error: ' + e.message;
    }
};

// Create job button
// Show/hide hybrid days based on working mode
const jobWorkingMode = document.getElementById('jobWorkingMode');
const hybridDaysGroup = document.getElementById('hybridDaysGroup');
if (jobWorkingMode && hybridDaysGroup) {
    jobWorkingMode.addEventListener('change', function() {
    const officeGroup = document.getElementById('officeLocationGroup');
    hybridDaysGroup.style.display = this.value === 'Hybrid' ? 'block' : 'none';
    if (officeGroup) {
        officeGroup.style.display = (this.value === 'Onsite' || this.value === 'Hybrid') ? 'block' : 'none';
        }
    });
}

// Create job button
const createJobBtn = document.getElementById('createJobBtn');
if (createJobBtn) createJobBtn.onclick = async function() {
    const data = {
        title: document.getElementById('jobTitle').value,
        company: document.getElementById('jobCompany').value,
        working_mode: document.getElementById('jobWorkingMode').value,
        hybrid_days: parseInt(document.getElementById('jobHybridDays').value) || 0, office_location: document.getElementById('jobOfficeLocation').value,
        business_model: document.getElementById('jobBusinessModel').value,
        payroll_company: document.getElementById('jobPayroll').value,
        end_client: document.getElementById('jobEndClient').value,
        years_of_experience: parseInt(document.getElementById('jobExperience').value) || 0,
        budget: document.getElementById('jobBudget').value,
        max_salary: document.getElementById('jobMaxSalary').value,
        headcount: parseInt(document.getElementById('jobHeadcount').value) || 1,
        roles_responsibilities: document.getElementById('jobRoles').value,
        qualifications: document.getElementById('jobQualifications').value,
        certifications_required: document.getElementById('jobCertifications').value,
        required_skills: document.getElementById('jobSkills').value,
        description: document.getElementById('jobDesc').value
    };
    
    if (!data.title) { toastError('Title is required'); return; }
    
    const res = await fetch('/api/jobs', { 
        method: 'POST', 
        headers: {'Content-Type':'application/json'}, 
        body: JSON.stringify(data) 
    });
    
    if (res.ok) { 
        toastSuccess('Requirement created!'); 
        document.getElementById('jobTitle').value = '';
        document.getElementById('jobCompany').value = '';
        document.getElementById('jobWorkingMode').value = 'Not Specified';
        document.getElementById('jobHybridDays').value = '0';
        document.getElementById('jobBusinessModel').value = 'Not Specified';
        document.getElementById('jobPayroll').value = '';
        document.getElementById('jobEndClient').value = '';
        document.getElementById('jobExperience').value = '0';
        document.getElementById('jobBudget').value = '';
        document.getElementById('jobHeadcount').value = '1';
        document.getElementById('jobRoles').value = '';
        document.getElementById('jobQualifications').value = '';
        document.getElementById('jobCertifications').value = '';
        document.getElementById('jobSkills').value = '';
        document.getElementById('jobDesc').value = '';
        if (hybridDaysGroup) hybridDaysGroup.style.display = 'none';
        showPanel('jobs'); 
        loadJobs(); 
    } else { 
        toastError('Error creating requirement'); 
    }
};
    
    const analyzeBtn = document.getElementById('analyzeBtn'); if (analyzeBtn) analyzeBtn.onclick = async function() {
    const jobId = document.getElementById('jobSelect').value;
    const candidateId = document.getElementById('candidateSelect').value;
    if(!jobId || !candidateId) return;
    const job = allJobs.find(j => j.id == jobId);
    const cand = allCandidates.find(c => c.id == candidateId);
    const div = document.getElementById('analysisResult');
    div.innerHTML = '<div class="spinner"></div><p>🤖 Analyzing with AI...</p>';
    const res = await fetch('/api/analyze-match', { 
        method: 'POST', 
        headers: {'Content-Type':'application/json'}, 
        body: JSON.stringify({ 
            job_id: jobId, 
            candidate_id: candidateId, 
            jd_text: job.description || '', 
            resume_text: cand.resume_text || '' 
        }) 
    });
    const result = await res.json();
    if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
    
    const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
    
    // Build category scores display
    let categoryHtml = '';
    if (result.category_scores) {
        const cats = result.category_scores;
       categoryHtml = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0;">
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.skills_match >= 70 ? '#1A237E' : (cats.skills_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Skills</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.skills_match || 0}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.experience_match >= 70 ? '#1A237E' : (cats.experience_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Experience</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.experience_match || 0}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.education_match >= 70 ? '#1A237E' : (cats.education_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Education</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.education_match || 0}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.certifications_match >= 70 ? '#1A237E' : (cats.certifications_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Certifications</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.certifications_match || 0}%</div>
        </div>
    </div>
`;
    }
    
    // Build skills display
    let skillsHtml = '';
        // Build genuineness display
    let genuinenessHtml = '';
    if (result.genuineness_score !== undefined) {
        const genClass = result.genuineness_score >= 70 ? 'match-high' : (result.genuineness_score >= 40 ? 'match-medium' : 'match-low');
        const aiClass = result.ai_generated_probability <= 30 ? 'match-high' : (result.ai_generated_probability <= 60 ? 'match-medium' : 'match-low');
        genuinenessHtml = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0;">
                <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
                    <div style="font-size: 11px; color: #666;">🔍 Authenticity</div>
                    <div style="font-size: 22px; font-weight: bold; margin-top: 4px;" class="${genClass}">${result.genuineness_score}%</div>
                </div>
                <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
                    <div style="font-size: 11px; color: #666;">🤖 AI Probability</div>
                    <div style="font-size: 22px; font-weight: bold; margin-top: 4px;" class="${aiClass}">${result.ai_generated_probability}%</div>
                </div>
            </div>
        `;
        
        if (result.red_flags && result.red_flags.length > 0) {
            genuinenessHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #B71C1C;">
                <strong style="color: #B71C1C; font-size: 14px;">🚨 Red Flags:</strong>
                <ul style="margin: 6px 0 0 0; padding-left: 20px; color: #B71C1C; font-size: 13px;">
                    ${result.red_flags.map(flag => `<li style="margin-bottom: 4px;">${escapeHtml(flag)}</li>`).join('')}
                </ul>
            </div>`;
        }
    }
 if (result.matching_skills && result.matching_skills.length > 0) {
    skillsHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #1A237E;">
        <strong style="color: #1A237E; font-size: 14px;">✅ Matching Skills:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.matching_skills.map(s => `<span style="background: #1A237E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
if (result.missing_skills && result.missing_skills.length > 0) {
    skillsHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #B71C1C;">
        <strong style="color: #B71C1C; font-size: 14px;">❌ Missing Skills:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.missing_skills.map(s => `<span style="background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
    
    // Build strengths/weaknesses
    let swotHtml = '';
    if (result.strengths && result.strengths.length > 0) {
 if (result.strengths && result.strengths.length > 0) {
    swotHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #1A237E;">
        <strong style="color: #1A237E; font-size: 14px;">💪 Strengths:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.strengths.map(s => `<span style="background: #1A237E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
if (result.weaknesses && result.weaknesses.length > 0) {
    swotHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #B71C1C;">
        <strong style="color: #B71C1C; font-size: 14px;">⚠️ Weaknesses:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.weaknesses.map(s => `<span style="background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
            }
    
    // Build questions
    let questionsHtml = '';
    if (result.pre_screening_questions && result.pre_screening_questions.length > 0) {
        questionsHtml = `<div style="margin-top: 10px;"><strong>📋 Pre-screening Questions:</strong><ul style="margin: 5px 0; padding-left: 20px;">`;
        result.pre_screening_questions.forEach(q => {
            questionsHtml += `<li>${escapeHtml(q)}</li>`;
        });
        questionsHtml += `</ul></div>`;
    }
    
    div.innerHTML = `
        <div class="alert-success" style="padding: 15px;">
            <h4>📊 Analysis Complete</h4>
            <div style="display: flex; align-items: center; gap: 20px; margin: 10px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 36px; font-weight: bold;" class="${matchClass}">${result.match_score || 0}%</div>
                    <div style="font-size: 12px; color: #666;">Match Score</div>
                </div>
                <div>
                    <div><strong>Recommendation:</strong> <span style="text-transform: uppercase; font-weight: bold;">${result.recommendation || 'Review'}</span></div>
                    <div style="font-size: 14px; color: #1A1A2E; margin-top: 8px; line-height: 1.7; background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #D0D8E4; max-height: 250px; overflow-y: auto; white-space: pre-wrap;">${result.detailed_analysis || result.executive_summary ? escapeHtml(result.detailed_analysis || result.executive_summary) : '<em style="color:#999;">No detailed analysis available</em>'}</div>
                </div>
            </div>
            ${categoryHtml}
            ${genuinenessHtml}
            ${skillsHtml}
            ${swotHtml}
            ${questionsHtml}
            
            <!-- INTERVIEW QUESTIONS -->
        ${result.interview_questions ? `
        <div style="margin-top: 15px; padding: 15px; background: #E3F2FD; border-radius: 8px; border-left: 4px solid #1A4D4A;">
            <h4 style="margin: 0 0 10px 0; color: #1A4D4A;">🎤 Interview Questions</h4>
            
            ${result.interview_questions.technical.length > 0 ? `
            <div style="margin: 8px 0;">
                <strong style="color: #1A4D4A;">💻 Technical Questions:</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${result.interview_questions.technical.map(q => `<li style="margin-bottom: 4px; color: #333;">${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}
            
            ${result.interview_questions.skill_check.length > 0 ? `
            <div style="margin: 8px 0;">
                <strong style="color: #1A4D4A;">🔍 Skill Check Questions:</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${result.interview_questions.skill_check.map(q => `<li style="margin-bottom: 4px; color: #333;">${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}
            
            ${result.interview_questions.behavioral.length > 0 ? `
            <div style="margin: 8px 0;">
                <strong style="color: #1A4D4A;">🧠 Behavioral Questions:</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${result.interview_questions.behavioral.map(q => `<li style="margin-bottom: 4px; color: #333;">${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}
        </div>` : ''}
                    // Add Skill Gap Analysis
        ${result.skill_gap ? `
        <div style="margin-top: 15px; padding: 15px; background: #F9F6F0; border-radius: 8px; border-left: 4px solid #C9A96E;">
            <h4 style="margin: 0 0 10px 0; color: #1A4D4A;">📊 Skill Gap Analysis</h4>
            
            <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 10px;">
                <div style="background: #E8F5E9; padding: 6px 14px; border-radius: 20px;">
                    <strong style="color: #1B5E20;">✅ Matching:</strong> 
                    <span style="color: #1B5E20; font-weight: bold;">${result.skill_gap.matching_skills.length}</span>
                </div>
                <div style="background: #FFEBEE; padding: 6px 14px; border-radius: 20px;">
                    <strong style="color: #B71C1C;">❌ Missing:</strong> 
                    <span style="color: #B71C1C; font-weight: bold;">${result.skill_gap.missing_skills.length}</span>
                </div>
                <div style="background: #FFF3E0; padding: 6px 14px; border-radius: 20px;">
                    <strong style="color: #E65100;">📊 Gap:</strong> 
                    <span style="color: #E65100; font-weight: bold;">${result.skill_gap.gap_percentage}%</span>
                </div>
            </div>
            
            ${result.skill_gap.matching_skills.length > 0 ? `
            <div style="margin: 10px 0;">
                <strong style="color: #1A4D4A;">✅ Matching Skills:</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
                    ${result.skill_gap.matching_skills.map(s => `<span style="background: #1B6B2E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
                </div>
            </div>` : ''}
            
            ${result.skill_gap.missing_skills.length > 0 ? `
            <div style="margin: 10px 0;">
                <strong style="color: #1A4D4A;">❌ Missing Skills:</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
                    ${result.skill_gap.missing_skills.map(s => `<span style="background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
                </div>
            </div>` : ''}
            
            ${result.skill_gap.learning_path.length > 0 ? `
            <div style="margin-top: 10px; background: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E8E0D8;">
                <strong style="color: #1A4D4A;">📚 Learning Path:</strong>
                <ul style="margin: 8px 0 0 0; padding-left: 20px; list-style-type: none;">
                    ${result.skill_gap.learning_path.map(item => `
                        <li style="margin-bottom: 10px; padding: 10px; background: #F9F6F0; border-radius: 6px; border-left: 3px solid #C9A96E;">
                            <strong style="color: #1A4D4A;">${escapeHtml(item.skill)}</strong>
                            <span style="background: #FFF3E0; color: #E65100; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 8px;">${item.estimated_hours} hours</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 20px; font-size: 12px; color: #555;">
                                ${item.resources.map(r => `<li style="margin-bottom: 3px; color: #555;">${escapeHtml(r)}</li>`).join('')}
                            </ul>
                        </li>
                    `).join('')}
                </ul>
            </div>` : ''}
        </div>` : ''}
            <small style="display: block; margin-top: 10px;">✅ Analysis saved to candidate record</small>
        </div>
    `;
    loadCandidates();
};
    
    // ========== BULK RESUME UPLOAD ==========
    document.getElementById('multiResumeFiles').addEventListener('change', function(e) {
        selectedBulkFiles = Array.from(e.target.files);
        const fileListDiv = document.getElementById('selectedFilesList');
        if (selectedBulkFiles.length > 0) {
            let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
            selectedBulkFiles.forEach((file, index) => {
                html += `<div class="file-list-item">📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)<span class="remove-file" onclick="removeBulkFile(${index})">✕ Remove</span></div>`;
            });
            fileListDiv.innerHTML = html;
            fileListDiv.style.display = 'block';
        } else {
            fileListDiv.style.display = 'none';
        }
    });
    
    window.removeBulkFile = function(index) {
        selectedBulkFiles.splice(index, 1);
        const dataTransfer = new DataTransfer();
        selectedBulkFiles.forEach(file => dataTransfer.items.add(file));
        document.getElementById('multiResumeFiles').files = dataTransfer.files;
        
        const fileListDiv = document.getElementById('selectedFilesList');
        if (selectedBulkFiles.length > 0) {
            let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
            selectedBulkFiles.forEach((file, idx) => {
                html += `<div class="file-list-item">📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)<span class="remove-file" onclick="removeBulkFile(${idx})">✕ Remove</span></div>`;
            });
            fileListDiv.innerHTML = html;
            fileListDiv.style.display = 'block';
        } else {
            fileListDiv.style.display = 'none';
        }
    };
    
    const bulkUploadBtn = document.getElementById('bulkUploadBtn'); if (bulkUploadBtn) bulkUploadBtn.onclick = async function() {
        if (selectedBulkFiles.length === 0) { toastWarning('Please select files first'); return; }
        
        const div = document.getElementById('bulkUploadResult');
        div.innerHTML = '<div class="spinner"></div><p>📚 Processing ' + selectedBulkFiles.length + ' files...</p>';
        
        let successCount = 0;
        let failCount = 0;
        let errors = [];
        
        for (let i = 0; i < selectedBulkFiles.length; i++) {
            const file = selectedBulkFiles[i];
            const fd = new FormData();
            fd.append('resume', file);
            
            const percent = Math.round((i / selectedBulkFiles.length) * 100);
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width: ${percent}%"></div></div>
    <div style="max-height: 300px; overflow-y: auto; margin-top: 10px;">
    <div><strong>📄 ${i+1} of ${selectedBulkFiles.length}:</strong> ${escapeHtml(file.name)}</div>
    <div id="liveStatus${i}" style="font-size: 13px; margin-left: 20px; margin-bottom: 10px;">⏳ Parsing...</div>
    </div>`;
            
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
document.getElementById(`liveStatus${i}`).innerHTML = result.error ? '❌ Parse failed: ' + escapeHtml(result.error) : '✅ Parsed successfully, saving...';
                
                 if (result.error) {
                    failCount++;
                    errors.push(`${file.name}: ${result.error}`);
                    document.getElementById(`liveStatus${i}`).innerHTML = '❌ Parse failed: ' + escapeHtml(result.error);
                } else {
                    // Check duplicate
                    const dupRes = await fetch('/api/candidates/check-duplicate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ email: result.email, phone: result.phone })
                    });
                    const dupData = await dupRes.json();
                    
                    if (dupData.duplicate) {
                        document.getElementById(`liveStatus${i}`).innerHTML = '⚠️ Duplicate skipped (matched by ' + dupData.matched_by + ')';
                        failCount++;
                        errors.push(`${file.name}: Duplicate - ${dupData.matches[0].first_name} ${dupData.matches[0].last_name}`);
                        continue; // Skip saving, move to next file
                    }
                    
                    // Save candidate
                                        // Save candidate
                    const bulkUploader = document.getElementById('bulkUploaderSelect').value;
                    if (!bulkUploader) { toastError('Please select uploader first'); return; }
                    result.uploaded_by = bulkUploader;
                    result.uploaded_by_name = bulkUploader;
                    
                    const saveRes = await fetch('/api/candidates', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify(result) 
                    });
                    document.getElementById(`liveStatus${i}`).innerHTML = saveRes.ok ? '✅ Saved! Resume auto-attached.' : '❌ Save failed';
                    if (saveRes.ok) {
                        successCount++;
                    } else {
                        failCount++;
                        errors.push(`${file.name}: Save failed`);
                    }
                }
                        } catch(e) {
                failCount++;
                errors.push(`${file.name}: ${e.message}`);
                document.getElementById(`liveStatus${i}`).innerHTML = `❌ Error: ${escapeHtml(e.message)}`;
            }
        }
        
        let resultHtml = `<div class="alert-success"><h4>✅ Bulk Upload Complete!</h4>`;
        resultHtml += `<p><strong>Total files:</strong> ${selectedBulkFiles.length}</p>`;
        resultHtml += `<p><strong>Successfully saved:</strong> ${successCount}</p>`;
        resultHtml += `<p><strong>Failed:</strong> ${failCount}</p>`;
        
        if (errors.length > 0 && errors.length <= 10) {
            resultHtml += `<div style="margin-top: 10px;"><strong>⚠️ Errors:</strong><ul>`;
            errors.forEach(err => { resultHtml += `<li>${escapeHtml(err)}</li>`; });
            resultHtml += `</ul></div>`;
        } else if (errors.length > 10) {
            resultHtml += `<p><strong>⚠️ ${errors.length} errors occurred. Check console for details.</strong></p>`;
        }
        
        resultHtml += `<button class="btn" onclick="document.getElementById('tabCandidates').click()" style="margin-top: 15px;">View All Candidates</button></div>`;
        div.innerHTML = resultHtml;
        
        // Clear selection
        selectedBulkFiles = [];
        document.getElementById('multiResumeFiles').value = '';
        document.getElementById('selectedFilesList').style.display = 'none';
        
        loadCandidates();
    };

        // ========== BATCH ANALYZE - Match JD Against ALL Candidates ==========
       const batchAnalyzeBtn = document.getElementById('batchAnalyzeBtn'); if (batchAnalyzeBtn) batchAnalyzeBtn.onclick = async function() {
        const jobId = document.getElementById('batchJobSelect').value;
       if (!jobId) { toastWarning('Please select a Job'); return; }
        
        const job = allJobs.find(j => j.id == jobId);
        if (!job) { toastWarning('Job not found'); return; }
        
        const div = document.getElementById('batchAnalysisResult');
        div.innerHTML = '<div class="spinner"></div><p>📊 Analyzing ' + allCandidates.length + ' candidates with enhanced matching...</p>';
        
        try {
            const res = await fetch('/api/batch-analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ jd_text: job.description || '' })
            });
            const results = await res.json();
            
            if (results.error) {
                div.innerHTML = `<div class="alert-error">${results.error}</div>`;
                return;
            }
            
            // Count candidates with meaningful match (>0%)
            const meaningfulMatches = results.filter(r => r.match_score > 0).length;
            
            let html = `<div class="alert-success" style="padding: 15px;"><h4>📊 Batch Analysis Complete</h4>`;
            html += `<div style="display: flex; gap: 20px; flex-wrap: wrap; margin: 10px 0;">`;
            html += `<div><strong>Job:</strong> ${escapeHtml(job.title)}</div>`;
            html += `<div><strong>Total Candidates:</strong> ${results.length}</div>`;
            html += `<div><strong>Candidates with any match (>0%):</strong> ${meaningfulMatches}</div>`;
            html += `</div><hr><div style="max-height: 500px; overflow-y: auto;">`;
            
            if (results.length === 0) {
                html += `<p style="color: #666; font-style: italic;">No candidates found in database.</p>`;
            } else {
               results.forEach((r, index) => {
    const matchClass = r.match_score >= 70 ? 'match-high' : (r.match_score >= 40 ? 'match-medium' : 'match-low');
    const nameDisplay = r.name && r.name !== 'Unknown' ? r.name : 'Unknown Candidate';
    
    // Medal emoji based on rank
    let medal = '';
    if (r.rank === 1) medal = '🥇';
    else if (r.rank === 2) medal = '🥈';
    else if (r.rank === 3) medal = '🥉';
    
    // Top 3 background highlight
    let bgStyle = '';
    if (r.rank === 1) bgStyle = 'background: linear-gradient(135deg, #FFF9C4 0%, #FFF176 100%); border-left: 4px solid #FFD700;';
    else if (r.rank === 2) bgStyle = 'background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); border-left: 4px solid #C0C0C0;';
    else if (r.rank === 3) bgStyle = 'background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%); border-left: 4px solid #CD7F32;';
    
    html += `<div class="card" style="cursor: pointer; margin: 8px 0; padding: 12px; border-left: 4px solid ${r.match_score >= 70 ? '#1B6B2E' : (r.match_score >= 40 ? '#CC5500' : '#B22222')}; ${bgStyle}">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div onclick="viewCandidate(${r.candidate_id})" style="flex: 1; cursor: pointer;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-weight: bold; color: #666; font-size: 16px; min-width: 40px;">${medal} #${r.rank}</span>
                    <span style="font-size: 16px; font-weight: bold;">👤 ${escapeHtml(nameDisplay)}</span>
                    ${r.rank <= 3 ? `<span style="background: #FFD700; color: #000; padding: 2px 12px; border-radius: 12px; font-size: 10px; font-weight: bold;">TOP ${r.rank}</span>` : ''}
                </div>
                ${r.email ? `<div style="font-size: 12px; color: #666; margin-top: 2px;">📧 ${escapeHtml(r.email)}</div>` : ''}
                ${r.tech_found && r.tech_found.length > 0 ? `<div style="font-size: 11px; color: #555; margin-top: 4px;">🔧 ${r.tech_found.map(t => `<span style="background: #E8F5E9; padding: 1px 8px; border-radius: 10px; margin: 2px; display: inline-block;">${escapeHtml(t)}</span>`).join(' ')}</div>` : ''}
                <div style="font-size: 11px; color: #999; margin-top: 4px;">
                    ${r.rank} of ${r.total_candidates} candidates
                </div>
            </div>
            <div style="text-align: right; min-width: 80px;">
                <div><span class="${matchClass}" style="font-size: 18px; padding: 4px 14px;">${r.match_score}%</span></div>
                <div style="font-size: 11px; margin-top: 2px; color: ${r.recommendation === 'hire' ? '#1B6B2E' : (r.recommendation === 'interview' ? '#CC5500' : '#B22222')};">
                    ${r.recommendation || 'Review'}
                </div>
                <button class="btn" style="background: #C9A96E; color: white; padding: 2px 10px; font-size: 10px; margin-top: 4px; border: none; border-radius: 4px; cursor: pointer;" onclick="event.stopPropagation(); runDeepAnalysis(${r.candidate_id}, '${escapeHtml(job.title)}')">🔍 AI Deep Dive</button>
            </div>
        </div>
    </div>`;
});
            }
            
            html += `</div>
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn" onclick="document.getElementById('tabCandidates').click()" style="margin-top:0;">👥 View All Candidates</button>
                    <button class="btn" onclick="document.getElementById('tabAnalyze').click(); loadJobs(); loadCandidates();" style="background: #C9A96E; margin-top:0;">🔍 Go to Single Analysis</button>
                </div>
            </div>`;
            div.innerHTML = html;
            
        } catch(e) {
            console.error('Batch analysis error:', e);
            div.innerHTML = '<div class="alert-error">❌ Analysis failed. Please try again.</div>';
        }
    };
      
           // ========== EXPORT PDF ==========
    window.exportPDF = async function(candidateId, event) {
        const btn = event.target;
        btn.textContent = '⏳ Generating...';
        btn.disabled = true;
        
        try {
            const res = await fetch(`/api/candidates/${candidateId}/export-pdf`);
            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // Get candidate name for filename
                const c = allCandidates.find(c => c.id == candidateId);
                const name = ((c.first_name || '') + '_' + (c.last_name || '')).trim() || 'candidate';
                a.download = `${name}_profile.pdf`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } else {
                toastError('Failed to generate PDF');
            }
        } catch(e) {
            toastError('Error generating PDF');
        } finally {
            btn.textContent = '📄 Export PDF';
            btn.disabled = false;
        }
    };
        // ========== STATUS MANAGEMENT ==========
    function getStatusColor(status) {
        const colors = {
            'new': '#2196F3',
            'screening': '#FF9800',
            'interview': '#FF5722',
            'offer': '#9C27B0',
            'hired': '#4CAF50',
            'rejected': '#F44336'
        };
        return colors[status] || '#666';
    }
    
    window.updateStatus = async function(candidateId, newStatus) {
        try {
            const res = await fetch(`/api/candidates/${candidateId}/status`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ employment_status: newStatus })
            });
            
            if (res.ok) {
                // Update the dropdown background color
                const dropdown = document.getElementById(`candidateStatus-${candidateId}`);
                if (dropdown) {
                    dropdown.style.background = getStatusColor(newStatus);
                }
                // Reload candidates list to reflect changes
                loadCandidates();
            } else {
                toastError('Failed to update status');
                // Reload to revert dropdown
                loadCandidates();
            }
        } catch(e) {
            toastError('Error updating status');
            loadCandidates();
        }
    };
        // ========== DASHBOARD ==========
    let matchChartInstance = null;
    let pipelineChartInstance = null;
    let trendChartInstance = null;

// ============================================
// USER MANAGEMENT
// ============================================

async function loadClients() {
    const res = await fetch('/api/client-analytics');
    const clients = await res.json();
    const container = document.getElementById('clientsList');
    
    if (!clients.length) {
        container.innerHTML = '<p style="text-align:center;padding:40px;color:#999;">No client data yet</p>';
        return;
    }
    
    container.innerHTML = clients.map(c => {
        const convColor = c.conversion >= 30 ? '#10B981' : c.conversion >= 15 ? '#F59E0B' : '#EF4444';
        return `<div class="card" style="margin:8px 0;width:100%;max-width:100%;">
            <h4 style="margin:0;">🏢 ${escapeHtml(c.name)}</h4>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:10px;">
                <div style="background:#F0F4FA;padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#1B2A4A;">${c.requirements}</div>
                    <div style="font-size:11px;color:#666;">Requirements</div>
                </div>
                <div style="background:#F0F4FA;padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#1B2A4A;">${c.proposals}</div>
                    <div style="font-size:11px;color:#666;">Proposals</div>
                </div>
                <div style="background:#F0F4FA;padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#1B2A4A;">${c.interviews}</div>
                    <div style="font-size:11px;color:#666;">Interviews</div>
                </div>
                <div style="background:#F0F4FA;padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#1B2A4A;">${c.closures}</div>
                    <div style="font-size:11px;color:#666;">Closures</div>
                </div>
                <div style="background:#F0F4FA;padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#0D9488;">₹${(c.revenue||0).toLocaleString()}</div>
                    <div style="font-size:11px;color:#666;">Monthly Revenue</div>
                </div>
                <div style="background:#F0F4FA;padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:${convColor};">${c.conversion}%</div>
                    <div style="font-size:11px;color:#666;">Conversion</div>
                </div>
            </div>
        </div>`;
    }).join('');
}

async function loadUsers() {
    try {
        const res = await fetch('/api/auth/users');
        if (!res.ok) { toastError('Admin access required'); return; }
        const users = await res.json();
        const container = document.getElementById('usersList');
        if (!users.length) {
            container.innerHTML = '<div class="card no-click" style="text-align:center;padding:30px;">No users found</div>';
            return;
        }
        container.innerHTML = users.map(u => `
            <div class="card" style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                    <div style="flex:1;min-width:200px;">
                        <strong>${escapeHtml(u.full_name)}</strong>
                        <span style="font-size:12px;color:#666;margin-left:8px;">${escapeHtml(u.email)}</span>
                        <span style="background:${u.role==='admin'?'#1B2A4A':u.role==='manager'?'#0D7B4A':'#6366F1'};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">${u.role.toUpperCase()}</span>
                        ${!u.is_active ? '<span style="background:#EF4444;color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">Disabled</span>' : ''}
                    </div>
                    <div style="display:flex;gap:6px;align-items:center;">
                        <select onchange="updateUserRole(${u.id}, this.value)" style="font-size:12px;padding:4px 8px;border-radius:6px;border:1px solid #D0D8E4;">
                            <option value="admin" ${u.role==='admin'?'selected':''}>Admin</option>
                            <option value="manager" ${u.role==='manager'?'selected':''}>Manager</option>
                            <option value="recruiter" ${u.role==='recruiter'?'selected':''}>Recruiter</option>
                        </select>
                        <button class="btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-secondary'}" onclick="toggleUserStatus(${u.id}, ${u.is_active ? 'false' : 'true'})" style="font-size:11px;padding:4px 10px;">
                            ${u.is_active ? '🚫 Disable' : '✅ Enable'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch(e) {
        toastError('Failed to load users');
    }
}

async function updateUserRole(userId, role) {
    const res = await fetch('/api/auth/users/' + userId, {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ role: role })
    });
    if (res.ok) { toastSuccess('Role updated'); loadUsers(); } else { toastError('Failed to update role'); }
}

async function toggleUserStatus(userId, isActive) {
    const res = await fetch('/api/auth/users/' + userId, {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ is_active: isActive })
    });
    if (res.ok) { toastSuccess(isActive ? 'User enabled' : 'User disabled'); loadUsers(); } else { toastError('Failed to update user'); }
}

document.addEventListener('DOMContentLoaded', function() {
    const addUserBtn = document.getElementById('addUserBtn');
    if (addUserBtn) addUserBtn.onclick = async function() {
        const full_name = document.getElementById('newUserName').value;
        const email = document.getElementById('newUserEmail').value;
        const password = document.getElementById('newUserPassword').value;
        const role = document.getElementById('newUserRole').value;
        const statusDiv = document.getElementById('addUserStatus');
        if (!full_name || !email || !password) { statusDiv.innerHTML = '<span style="color:#EF4444;">All fields required</span>'; return; }
        statusDiv.innerHTML = '<span style="color:#6366F1;">Creating...</span>';
        const res = await fetch('/api/auth/users', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ full_name, email, password, role })
        });
        if (res.ok) {
            statusDiv.innerHTML = '<span style="color:#10B981;">✅ User created!</span>';
            document.getElementById('newUserName').value = '';
            document.getElementById('newUserEmail').value = '';
            document.getElementById('newUserPassword').value = '';
            loadUsers();
        } else {
            const data = await res.json();
            statusDiv.innerHTML = '<span style="color:#EF4444;">' + (data.error || 'Failed') + '</span>';
        }
    };
});

async function testTelegram() {
    const res = await fetch('/api/telegram/daily-digest', { method: 'POST' });
    if (res.ok) {
        toastSuccess('Telegram message sent! Check the group.');
    } else {
        toastError('Failed to send Telegram message');
    }
}

async function triggerBackup() {
    const div = document.getElementById('backupStatus');
    div.innerHTML = '<span style="color:#6366F1;">⏳ Creating backup...</span>';
    try {
        const res = await fetch('/api/admin/backup', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            const driveMsg = data.drive_upload ? '✅ Uploaded to Google Drive' : '⚠️ Local only';
            div.innerHTML = `<span style="color:#10B981;">✅ Backup saved: ${data.filename}</span><br><span>${driveMsg}</span>`;
        } else {
            div.innerHTML = `<span style="color:#EF4444;">❌ ${data.error}</span>`;
        }
    } catch(e) {
        div.innerHTML = '<span style="color:#EF4444;">❌ Backup failed</span>';
    }
}

async function listBackups() {
    const div = document.getElementById('backupStatus');
    try {
        const res = await fetch('/api/admin/backups');
        const data = await res.json();
        if (data.backups && data.backups.length > 0) {
            div.innerHTML = '<strong>📂 Backups:</strong><br>' + data.backups.slice(0,10).map(b => 
                `<a href="/api/admin/backup/download/${b.filename}" style="color:#1B2A4A;">📥 ${b.filename}</a> (${b.size})`
            ).join('<br>');
        } else {
            div.innerHTML = '<span style="color:#666;">No backups found</span>';
        }
    } catch(e) {
        div.innerHTML = '<span style="color:#EF4444;">Failed to load backups</span>';
    }
}
    
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard-data');
            const data = await res.json();
            
            // Update stats cards
            document.getElementById('totalCandidates').textContent = data.total || 0;
            document.getElementById('matchedCandidates').textContent = data.matched || 0;
            document.getElementById('hiredCandidates').textContent = data.hired || 0;
            document.getElementById('rejectedCandidates').textContent = data.rejected || 0;
            
            // Render match score chart
            renderMatchChart(data.matchDistribution || {});
            
            // Render pipeline chart
            renderPipelineChart(data.pipeline || {});
            
            // Render skills cloud
            renderSkillsCloud(data.skills || []);
            
            // Render trend chart
            renderTrendChart(data.trend || {});
            
        } catch(e) {
            console.error('Dashboard error:', e);
        }
    }
    
    function renderMatchChart(distribution) {
        const ctx = document.getElementById('matchChart').getContext('2d');
        const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
        const values = [
            distribution['0-20'] || 0,
            distribution['21-40'] || 0,
            distribution['41-60'] || 0,
            distribution['61-80'] || 0,
            distribution['81-100'] || 0
        ];
        const colors = ['#F44336', '#FF9800', '#FFC107', '#4CAF50', '#1B6B2E'];
        
        if (matchChartInstance) {
            matchChartInstance.destroy();
        }
        
        matchChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Candidates',
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(c => c),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
    
function renderPipelineChart(pipeline) {
    const canvas = document.getElementById('pipelineChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    const labels = ['New', 'Proposed', 'Screening', 'Tech L1', 'Tech L2', 'Tech L3', 'Rejected', 'Shortlisted', 'Offer Shared', 'Onboarded'];
    const values = [
        pipeline.new || 0,
        pipeline.proposed || 0,
        pipeline.screening || 0,
        pipeline.technical_l1 || 0,
        pipeline.technical_l2 || 0,
        pipeline.technical_l3 || 0,
        pipeline.rejected || 0,
        pipeline.shortlisted || 0,
        pipeline.offer_letter_shared || 0,
        pipeline.onboarded || 0
    ];
    const colors = [
        '#1B5F8C',  // New - Blue
        '#6B4CB8',  // Proposed - Purple
        '#B85C00',  // Screening - Orange
        '#0D7B4A',  // Tech L1 - Green
        '#0D7B4A',  // Tech L2 - Green
        '#0A5C35',  // Tech L3 - Dark Green
        '#C42020',  // Rejected - Red
        '#D4A800',  // Shortlisted - Gold
        '#2C7A4A',  // Offer Shared - Green
        '#1B5F8C'   // Onboarded - Blue
    ];
    
    if (pipelineChartInstance) pipelineChartInstance.destroy();
    
    pipelineChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: { 
            labels: labels, 
            datasets: [{ 
                data: values, 
                backgroundColor: colors, 
                borderColor: '#fff', 
                borderWidth: 2 
            }] 
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: true, 
            plugins: { 
                legend: { 
                    position: 'right', 
                    labels: { boxWidth: 12, font: { size: 10 } } 
                } 
            } 
        }
    });
}
    
    function renderSkillsCloud(skills) {
    const container = document.getElementById('skillsCloud');
    if (!container) return;
    if (!skills || skills.length === 0) { 
        container.innerHTML = '<p style="color: #999; font-style: italic;">No skills data available</p>'; 
        return; 
    }
    
    const normalizedSkills = skills.map(s => 
        typeof s === 'object' ? {skill: s.skill || s.name || '', count: s.count || 1} : {skill: String(s), count: 1}
    );
    const topSkills = normalizedSkills.slice(0, 15);
    const maxCount = topSkills[0]?.count || 1;
    
    container.innerHTML = topSkills.map(s => {
        const size = 10 + (s.count / maxCount) * 8;
        return '<span style="font-size:' + size + 'px; color:#1A4D4A; background:#F5F0E8; padding:4px 12px; border-radius:20px; border:1px solid #ddd; opacity:' + (0.6 + (s.count / maxCount) * 0.4) + ';">' + escapeHtml(s.skill) + '</span>';
    }).join('');
}
    
    function renderTrendChart(trend) {
        const ctx = document.getElementById('trendChart').getContext('2d');
        const labels = trend.labels || [];
        const values = trend.values || [];
        
        if (trendChartInstance) {
            trendChartInstance.destroy();
        }
        
        if (labels.length === 0) {
            trendChartInstance = null;
            return;
        }
        
        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Candidates Added',
                    data: values,
                    borderColor: '#1A4D4A',
                    backgroundColor: 'rgba(26, 77, 74, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#1A4D4A'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    // ========== DASHBOARD ==========
// ============================================
// KANBAN BOARD
// ============================================

const kanbanStages = [
    { id: 'new', name: 'New', color: '#2196F3', emoji: '🆕' },
    { id: 'proposed', name: 'Proposed', color: '#6B4CB8', emoji: '📋' },
    { id: 'screening', name: 'Screening', color: '#FF9800', emoji: '🔍' },
    { id: 'technical_l1', name: 'L1 Tech', color: '#0D7B4A', emoji: '💻' },
    { id: 'technical_l2', name: 'L2 Tech', color: '#0D7B4A', emoji: '💻' },
    { id: 'technical_l3', name: 'L3 Tech', color: '#0A5C35', emoji: '💻' },
    { id: 'shortlisted', name: 'Shortlisted', color: '#D4A800', emoji: '⭐' },
    { id: 'offer_letter_shared', name: 'Offer', color: '#2C7A4A', emoji: '📄' },
    { id: 'onboarded', name: 'Onboarded', color: '#1B5F8C', emoji: '✅' },
    { id: 'rejected', name: 'Rejected', color: '#C42020', emoji: '❌' }
];

function searchOnbCandidate() {
    const search = document.getElementById('onbCandidate').value.toLowerCase();
    const list = document.getElementById('onbCandidateList');
    if (!search || search.length < 1) { list.innerHTML = ''; return; }
    const matches = allCandidates.filter(c => 
        (c.first_name + ' ' + c.last_name).toLowerCase().includes(search) ||
        String(c.id).padStart(3,'0').includes(search)
    );
    list.innerHTML = matches.map(c => 
        `<option value="${String(c.id).padStart(3,'0')} - ${escapeHtml((c.first_name||'') + ' ' + (c.last_name||''))}">`
    ).join('');
}

function searchOnbRequirement() {
    const search = document.getElementById('onbRequirementId').value.toLowerCase();
    const list = document.getElementById('onbReqList');
    if (!search || search.length < 1) { list.innerHTML = ''; return; }
    const matches = allJobs.filter(j => 
        (j.requirement_id || '').toLowerCase().includes(search) ||
        (j.title || '').toLowerCase().includes(search)
    );
    list.innerHTML = matches.map(j => 
        `<option value="${(j.requirement_id || 'SIT-R-'+String(j.id).padStart(3,'0')).replace('SIT-R-','')} - ${escapeHtml(j.title || '')}">`
    ).join('');
}

async function editOnboarded(id) {
    const res = await fetch('/api/onboarded');
    const resources = await res.json();
    const r = resources.find(r => r.id == id);
    if (!r) return;
    
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `<div style="background:#fff;padding:25px;border-radius:12px;width:90%;max-width:500px;max-height:80vh;overflow-y:auto;">
        <h3>✏️ Edit Onboarded Resource</h3>
        <label>Client</label><input id="editOnbClient" class="form-input" value="${escapeHtml(r.client_name||'')}">
        <label>DOJ</label><input id="editOnbDOJ" type="date" class="form-input" value="${r.doj||''}">
        <label>Resource Owner</label><input id="editOnbOwner" class="form-input" value="${escapeHtml(r.resource_owner||'')}">
        <label>Work Location</label><input id="editOnbLocation" class="form-input" value="${escapeHtml(r.work_location||'')}">
        <label>Monthly Salary (₹)</label><input id="editOnbSalary" type="number" class="form-input" value="${r.monthly_salary||0}">
        <label>Billing Rate (₹)</label><input id="editOnbBilling" type="number" class="form-input" value="${r.billing_rate||0}">
        <label>Business Model</label><select id="editOnbModel" class="form-input">
            <option value="C2C" ${r.business_model==='C2C'?'selected':''}>C2C</option>
            <option value="C2H" ${r.business_model==='C2H'?'selected':''}>C2H</option>
            <option value="FTE" ${r.business_model==='FTE'?'selected':''}>FTE</option>
            <option value="Fixed Price" ${r.business_model==='Fixed Price'?'selected':''}>Fixed Price</option>
        </select>
        <label>Requirement ID</label><input id="editOnbReq" class="form-input" value="${escapeHtml(r.requirement_id||'')}">
        <label>PO Number</label><input id="editOnbPO" class="form-input" value="${escapeHtml(r.po_number||'')}">
        <label>Status</label><select id="editOnbStatus" class="form-input">
            <option value="Active" ${r.status==='Active'?'selected':''}>Active</option>
            <option value="Completed" ${r.status==='Completed'?'selected':''}>Completed</option>
            <option value="Terminated" ${r.status==='Terminated'?'selected':''}>Terminated</option>
        </select>
                <label>Attach Documents</label><input type="file" id="editOnbDocs" multiple accept=".pdf,.docx,.doc" style="font-size:12px;">
        <div style="margin-top:15px;display:flex;gap:10px;">
            <button id="saveOnbEdit" class="btn btn-primary">💾 Save</button>
            <button id="cancelOnbEdit" class="btn btn-secondary">Cancel</button>
        </div>
    </div>`;
    document.body.appendChild(modal);
    
    document.getElementById('cancelOnbEdit').onclick = () => modal.remove();
        document.getElementById('saveOnbEdit').onclick = async () => {
        const formData = new FormData();
        formData.append('client_name', document.getElementById('editOnbClient').value);
        formData.append('doj', document.getElementById('editOnbDOJ').value);
        formData.append('resource_owner', document.getElementById('editOnbOwner').value);
        formData.append('work_location', document.getElementById('editOnbLocation').value);
        formData.append('monthly_salary', document.getElementById('editOnbSalary').value);
        formData.append('billing_rate', document.getElementById('editOnbBilling').value);
        formData.append('business_model', document.getElementById('editOnbModel').value);
        formData.append('requirement_id', document.getElementById('editOnbReq').value);
        formData.append('po_number', document.getElementById('editOnbPO').value);
        formData.append('status', document.getElementById('editOnbStatus').value);
        
        const docFiles = document.getElementById('editOnbDocs').files;
        for (let i = 0; i < docFiles.length; i++) {
            formData.append('documents', docFiles[i]);
        }
        
        const updateRes = await fetch('/api/onboarded/' + id, {
            method: 'PUT',
            body: formData
        });
        if (updateRes.ok) {
            toastSuccess('Updated!');
            modal.remove();
            loadOnboarded();
        } else {
            toastError('Failed to update');
        }
    };
}
async function openCompanySettings() {
    const res = await fetch('/api/company-settings');
    const settings = await res.json();
    document.getElementById('setBankName').value = settings.bank_name || '';
    document.getElementById('setAccountNo').value = settings.account_no || '';
    document.getElementById('setIfsc').value = settings.ifsc_code || '';
    document.getElementById('setBranch').value = settings.branch || '';
    document.getElementById('setSignatory').value = settings.authorized_signatory || '';
    document.getElementById('companySettingsModal').style.display = 'block';
}

function closeCompanySettings() {
    document.getElementById('companySettingsModal').style.display = 'none';
}

async function saveCompanySettings() {
    const data = {
        bank_name: document.getElementById('setBankName').value,
        account_no: document.getElementById('setAccountNo').value,
        ifsc_code: document.getElementById('setIfsc').value,
        branch: document.getElementById('setBranch').value,
        authorized_signatory: document.getElementById('setSignatory').value
    };
    
    await fetch('/api/company-settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    const logoFile = document.getElementById('logoFile').files[0];
    if (logoFile) {
        const fd = new FormData();
        fd.append('logo', logoFile);
        await fetch('/api/upload-logo', { method: 'POST', body: fd });
    }
    
    toastSuccess('Settings saved!');
    closeCompanySettings();
}
async function loadInvoices() {
    const res = await fetch('/api/invoices');
    const invoices = await res.json();
    const container = document.getElementById('invoicesList');
    
    let html = `<div style="margin-bottom:15px;">
        <strong>➕ Generate Invoice for Resource:</strong>
        <select id="invoiceResourceSelect" class="form-input" style="width:250px;display:inline-block;margin:0 10px;">
            <option value="">-- Select Resource --</option>
        </select>
        <input type="date" id="invoiceDate" class="form-input" style="width:150px;display:inline-block;margin-right:10px;" value="${new Date().toISOString().split('T')[0]}">
        <button class="btn btn-primary" onclick="generateInvoice()">📄 Generate Invoice</button>
    </div>`;
    
    if (!invoices.length) {
        html += '<p style="text-align:center;padding:40px;color:#999;">No invoices yet</p>';
    } else {
        invoices.forEach(inv => {
            const statusColor = inv.status === 'Paid' ? '#10B981' : inv.status === 'Sent' ? '#F59E0B' : inv.status === 'Overdue' ? '#EF4444' : '#6366F1';
            html += `<div class="card" style="margin:8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                    <div>
                        <strong>${escapeHtml(inv.invoice_number)}</strong> - ${escapeHtml(inv.client_name)}
                        <span style="background:${statusColor};color:#fff;padding:2px 10px;border-radius:10px;font-size:11px;margin-left:8px;">${inv.status}</span>
                    </div>
                    <div style="font-size:13px;">
                        ₹${(inv.total_amount||0).toLocaleString()} | ${inv.invoice_date}
                        <button class="btn btn-sm" onclick="viewInvoicePDF(${inv.id})" style="margin-left:8px;">📄 View</button>
                        ${inv.status === 'Draft' || inv.status === 'Sent' ? `<button class="btn btn-sm btn-secondary" onclick="markInvoicePaid(${inv.id})" style="margin-left:4px;">✅ Mark Paid</button>` : ''}
                    </div>
                </div>
            </div>`;
        });
    }
    
    container.innerHTML = html;
    
    // Populate resource dropdown
    const resRes = await fetch('/api/onboarded');
    const resources = await resRes.json();
    document.getElementById('invoiceResourceSelect').innerHTML = '<option value="">-- Select Resource --</option>' + 
        resources.map(r => `<option value="${r.id}">${escapeHtml(r.client_name||'N/A')} - ${escapeHtml(r.first_name||'')} ${escapeHtml(r.last_name||'')}</option>`).join('');
}

async function generateInvoice() {
    const resourceId = document.getElementById('invoiceResourceSelect').value;
    if (!resourceId) { toastError('Select a resource'); return; }
    const date = document.getElementById('invoiceDate').value;
    
    const res = await fetch('/api/invoices', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ onboarded_resource_id: parseInt(resourceId), invoice_date: date, description: 'Professional Services' })
    });
    if (res.ok) {
        toastSuccess('Invoice generated!');
        loadInvoices();
    } else {
        toastError('Failed to generate invoice');
    }
}

async function viewInvoicePDF(invoiceId) {
    const res = await fetch('/api/invoices');
    const invoices = await res.json();
    const inv = invoices.find(i => i.id == invoiceId);
    if (!inv) return;
    
    // Get client details
    const resRes = await fetch('/api/onboarded');
    const resources = await resRes.json();
    const resource = resources.find(r => r.id == inv.onboarded_resource_id);
    
    const settingsRes = await fetch('/api/company-settings');
    const settings = await settingsRes.json();
    
    document.getElementById('editInvClient').value = inv.client_name || '';
    document.getElementById('editInvGstin').value = (resource && resource.client_gstin) || '';
    document.getElementById('editInvAddress').value = (resource && resource.client_address) || '';
    document.getElementById('editInvDate').value = inv.invoice_date || '';
    document.getElementById('editInvDueDate').value = inv.due_date || '';
    document.getElementById('editInvDesc').value = inv.description || '';
    document.getElementById('editInvAmount').value = inv.amount || 0;
    document.getElementById('editInvGst').value = inv.gst_percent || 18;
    document.getElementById('editInvBank').value = settings.bank_name || '';
    document.getElementById('editInvAcc').value = settings.account_no || '';
    document.getElementById('editInvIfsc').value = settings.ifsc_code || '';
    document.getElementById('editInvBranch').value = settings.branch || '';
    
    document.getElementById('editInvoiceModal').style.display = 'block';
    document.getElementById('editInvoiceModal').setAttribute('data-invoice-id', invoiceId);
}

function closeEditInvoice() {
    document.getElementById('editInvoiceModal').style.display = 'none';
}

async function saveEditedInvoice() {
    const invoiceId = document.getElementById('editInvoiceModal').getAttribute('data-invoice-id');
    const data = {
        client_name: document.getElementById('editInvClient').value,
        invoice_date: document.getElementById('editInvDate').value,
        due_date: document.getElementById('editInvDueDate').value,
        description: document.getElementById('editInvDesc').value,
        amount: parseFloat(document.getElementById('editInvAmount').value) || 0,
        gst_percent: parseFloat(document.getElementById('editInvGst').value) || 0,
        bank_name: document.getElementById('editInvBank').value,
        account_no: document.getElementById('editInvAcc').value,
        ifsc_code: document.getElementById('editInvIfsc').value,
        branch: document.getElementById('editInvBranch').value,
        client_gstin: document.getElementById('editInvGstin').value,
        client_address: document.getElementById('editInvAddress').value
    };
    
    // Save invoice edits
    await fetch('/api/invoices/' + invoiceId + '/edit', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    closeEditInvoice();
    window.open('/api/invoices/' + invoiceId + '/pdf', '_blank');
}

async function markInvoicePaid(invoiceId) {
    const date = prompt('Payment date (YYYY-MM-DD):', new Date().toISOString().split('T')[0]);
    if (!date) return;
    const res = await fetch('/api/invoices/' + invoiceId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ status: 'Paid', payment_date: date })
    });
    if (res.ok) { toastSuccess('Marked as paid!'); loadInvoices(); }
    else { toastError('Failed to update'); }
}
function exportCandidatesCSV() { window.open('/api/export-candidates', '_blank'); }
function exportCandidatesPDF() { window.open('/api/admin/export-pdf', '_blank'); }
function exportInvoicesCSV() { window.open('/api/export-invoices', '_blank'); }
function exportExpensesCSV() { window.open('/api/export-expenses', '_blank'); }
function exportInterviewsCSV() { window.open('/api/export-interviews', '_blank'); }
function exportFinancePDF() { window.open('/api/export-finance-pdf', '_blank'); }
async function loadExpenses() {
    const res = await fetch('/api/expenses');
    const expenses = await res.json();
    const container = document.getElementById('expensesList');
    
    if (!expenses.length) {
        container.innerHTML = '<p style="text-align:center;padding:40px;color:#999;">No expenses yet</p>';
        return;
    }
    
    let total = 0;
    expenses.forEach(e => total += e.amount || 0);
    
    let html = `<div class="alert-success" style="margin:10px 0;"><strong>Total Expenses: ₹${total.toLocaleString()}</strong> (${expenses.length} entries)</div>`;
    
    expenses.forEach(e => {
        html += `<div class="card" style="margin:8px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div>
                    <strong>${escapeHtml(e.category)}</strong> - ${escapeHtml(e.description||'N/A')}
                    <div style="font-size:12px;color:#777;">📅 ${e.expense_date} | 👤 ${escapeHtml(e.paid_by||'N/A')} | 🏢 ${escapeHtml(e.vendor||'N/A')}</div>
                    ${e.invoice_ref ? `<a href="/api/expenses/${e.id}/download-bill" style="font-size:12px;color:#1B2A4A;text-decoration:underline;">📎 View Bill</a>` : ''}
                </div>
                <div style="font-size:16px;font-weight:bold;color:#EF4444;">₹${(e.amount||0).toLocaleString()}</div>
            </div>
        </div>`;
    });
    
    container.innerHTML = html;
}
async function loadFinance() {
    const res = await fetch('/api/finance-dashboard');
    const data = await res.json();
    
    document.getElementById('finTotalRevenue').textContent = '₹' + (data.total_revenue || 0).toLocaleString();
    document.getElementById('finTotalSalary').textContent = '₹' + (data.total_salary || 0).toLocaleString();
    document.getElementById('finTotalProfit').textContent = '₹' + (data.total_profit || 0).toLocaleString();
    document.getElementById('finAvgMargin').textContent = (data.avg_margin || 0) + '%';
    document.getElementById('finActiveResources').textContent = data.active_resources || 0;
    
    let html = '<h4>📊 Client-wise Breakdown</h4>';
    const clients = data.clients || {};
    
    for (const [client, info] of Object.entries(clients)) {
        const profit = info.revenue - info.salary;
        const margin = info.revenue > 0 ? Math.round((profit / info.revenue) * 100) : 0;
        html += `<div class="card" style="margin:8px 0;">
            <h4>🏢 ${escapeHtml(client)} <span style="font-size:12px;color:#666;">(${info.count} resources)</span></h4>
            <div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;">
                <span>💰 Revenue: <strong>₹${info.revenue.toLocaleString()}</strong></span>
                <span>💸 Salary: <strong>₹${info.salary.toLocaleString()}</strong></span>
                <span style="color:${margin>=30?'#10B981':margin>=15?'#F59E0B':'#EF4444'};font-weight:bold;">📊 Margin: ${margin}% (₹${profit.toLocaleString()})</span>
            </div>
            <div style="margin-top:8px;font-size:12px;">`;
        info.resources.forEach(r => {
            html += `<div style="padding:2px 0;">👤 ${escapeHtml(r.name)} - Salary: ₹${r.salary.toLocaleString()} | Billing: ₹${r.billing.toLocaleString()} | Margin: ${r.margin}%</div>`;
        });
        html += `</div></div>`;
    }
    
    document.getElementById('financeBreakdown').innerHTML = html || '<p style="color:#999;">No active resources</p>';
}
async function generatePayslip(resourceId) {
    const res = await fetch('/api/onboarded');
    const resources = await res.json();
    const r = resources.find(r => r.id == resourceId);
    if (!r) return;
    
    const salary = r.monthly_salary || 0;
    
    document.getElementById('editPayName').value = `${r.first_name||''} ${r.last_name||''}`.trim();
    document.getElementById('editPayDesignation').value = r.work_location || '';
    document.getElementById('editPayPeriod').value = `${new Date().toLocaleString('default',{month:'long'})} ${new Date().getFullYear()}`;
    document.getElementById('editPayBasic').value = Math.round(salary * 0.4);
    document.getElementById('editPayHra').value = Math.round(salary * 0.2);
    document.getElementById('editPayConveyance').value = Math.round(salary * 0.15);
    document.getElementById('editPayMedical').value = Math.round(salary * 0.1);
    document.getElementById('editPaySpecial').value = Math.round(salary * 0.15);
    document.getElementById('editPayPf').value = Math.round(salary * 0.12);
    document.getElementById('editPayPt').value = 200;
    
    document.getElementById('editPayslipModal').style.display = 'block';
}

function closeEditPayslip() {
    document.getElementById('editPayslipModal').style.display = 'none';
}

function saveEditedPayslip() {
    const name = document.getElementById('editPayName').value;
    const designation = document.getElementById('editPayDesignation').value;
    const period = document.getElementById('editPayPeriod').value;
    const days = parseInt(document.getElementById('editPayDays').value) || 30;
    const basic = parseFloat(document.getElementById('editPayBasic').value) || 0;
    const hra = parseFloat(document.getElementById('editPayHra').value) || 0;
    const conveyance = parseFloat(document.getElementById('editPayConveyance').value) || 0;
    const medical = parseFloat(document.getElementById('editPayMedical').value) || 0;
    const special = parseFloat(document.getElementById('editPaySpecial').value) || 0;
    const pf = parseFloat(document.getElementById('editPayPf').value) || 0;
    const pt = parseFloat(document.getElementById('editPayPt').value) || 0;
    
    const gross = basic + hra + conveyance + medical + special;
    const deductions = pf + pt;
    const netPay = gross - deductions;
    
    closeEditPayslip();
    
    const win = window.open('', '_blank', 'width=800,height=900');
    win.document.write(`<html><head><title>Payslip</title>
    <style>
        body { font-family: 'Times New Roman', serif; max-width: 750px; margin: 0 auto; padding: 30px; color: #3D3D3D; background: #FFF; }
        .header { text-align: center; border-bottom: 3px solid #0D9488; padding-bottom: 15px; margin-bottom: 20px; }
        .header h1 { color: #1A237E; font-size: 22px; margin: 0; }
        .header .subtitle { color: #0D9488; font-size: 13px; margin: 5px 0 0 0; }
        .payslip-box { background: #F5F0E8; border: 2px solid #C9A96E; border-radius: 10px; padding: 15px 20px; margin: 15px 0; text-align: center; }
        .payslip-box h2 { color: #1A237E; font-size: 24px; margin: 0; }
        .payslip-box .address { font-size: 11px; color: #666; margin: 3px 0 0 0; }
        .info-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .info-table td { padding: 8px 12px; font-size: 13px; }
        .info-table .label { font-weight: 700; color: #1A237E; width: 35%; background: #F5F0E8; }
        .main-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .main-table th { background: #0D9488; color: #FFF; padding: 10px; text-align: left; font-size: 13px; }
        .main-table td { padding: 8px 10px; border-bottom: 1px solid #E2E0D8; font-size: 13px; }
        .main-table .total td { font-weight: 700; color: #1A237E; border-top: 2px solid #C9A96E; }
        .net-pay { background: #0D9488; color: #FFF; text-align: center; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .net-pay .fig { font-size: 26px; font-weight: 700; }
        .net-pay .words { font-size: 13px; opacity: 0.9; margin-top: 4px; }
        .footer { text-align: center; font-size: 10px; color: #999; margin-top: 25px; font-style: italic; }
    </style></head><body>
    <div class="header">
        <h1>ShahnaIT LLP</h1>
        <div class="subtitle">IT Consultancy & Managed Service</div>
    </div>
    <div class="payslip-box">
        <h2>Payslip</h2>
        <div class="address">Ground Floor, 4-617/113, Mansabdar Layout, Near Jamiya Masjid, MB Nagar, Kalaburagi, Karnataka 585105</div>
    </div>
    <table class="info-table">
        <tr><td class="label">Employee Name</td><td>${name}</td></tr>
        <tr><td class="label">Designation</td><td>${designation}</td></tr>
        <tr><td class="label">Pay Period</td><td>${period}</td></tr>
        <tr><td class="label">Worked Days</td><td>${days}</td></tr>
    </table>
    <table class="main-table">
        <tr><th>Earnings</th><th style="text-align:right;">Amount (₹)</th><th>Deductions</th><th style="text-align:right;">Amount (₹)</th></tr>
        <tr><td>Basic Salary</td><td style="text-align:right;">${basic.toLocaleString()}</td><td>Provident Fund</td><td style="text-align:right;">${pf.toLocaleString()}</td></tr>
        <tr><td>HRA</td><td style="text-align:right;">${hra.toLocaleString()}</td><td>Professional Tax</td><td style="text-align:right;">${pt.toLocaleString()}</td></tr>
        <tr><td>Conveyance</td><td style="text-align:right;">${conveyance.toLocaleString()}</td><td></td><td></td></tr>
        <tr><td>Medical Allowance</td><td style="text-align:right;">${medical.toLocaleString()}</td><td></td><td></td></tr>
        <tr><td>Special Allowance</td><td style="text-align:right;">${special.toLocaleString()}</td><td></td><td></td></tr>
        <tr class="total"><td>Gross Earnings</td><td style="text-align:right;">${gross.toLocaleString()}</td><td>Total Deductions</td><td style="text-align:right;">${deductions.toLocaleString()}</td></tr>
    </table>
    <div class="net-pay">
        <div class="fig">Net Pay: ₹${netPay.toLocaleString()}</div>
        <div class="words">(Rupees ${numberToWords(Math.round(netPay))} only)</div>
    </div>
    <div class="footer">This is a system generated payslip</div>
    </body></html>`);
}

function numberToWords(num) {
    if (num === 0) return 'Zero';
    const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
    if (num < 20) return ones[num];
    if (num < 100) return tens[Math.floor(num/10)] + (num%10 ? ' ' + ones[num%10] : '');
    if (num < 1000) return ones[Math.floor(num/100)] + ' Hundred' + (num%100 ? ' ' + numberToWords(num%100) : '');
    if (num < 100000) return numberToWords(Math.floor(num/1000)) + ' Thousand' + (num%1000 ? ' ' + numberToWords(num%1000) : '');
    return numberToWords(Math.floor(num/100000)) + ' Lakh' + (num%100000 ? ' ' + numberToWords(num%100000) : '');
}

async function loadOnboarded() {
    const res = await fetch('/api/onboarded');
    const resources = await res.json();
    const container = document.getElementById('onboardedList');
    if (!resources.length) {
        container.innerHTML = '<div class="card no-click" style="text-align:center;padding:40px;">No onboarded resources</div>';
        return;
    }
    container.innerHTML = resources.map(r => {
        const revenue = (r.billing_rate || 0) - (r.monthly_salary || 0);
        const margin = r.billing_rate ? Math.round((revenue / r.billing_rate) * 100) : 0;
        return `<div class="card" style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:10px;">
                <div style="flex:1;"><h4 style="margin:0;"><strong style="color:#1B2A4A;">${escapeHtml(r.first_name||'')} ${escapeHtml(r.last_name||'')}</strong></h4>
                <div style="font-size:13px;color:#555;">🏢 ${escapeHtml(r.client_name||'N/A')} | 📅 DOJ: ${r.doj||'N/A'}</div>
                <div style="font-size:12px;color:#777;">👤 ${escapeHtml(r.resource_owner||'N/A')} | 📍 ${escapeHtml(r.work_location||'N/A')}</div></div>
                <div style="text-align:right;"><div>💰 Salary: ₹${(r.monthly_salary||0).toLocaleString()}</div>
                <div>📊 Billing: ₹${(r.billing_rate||0).toLocaleString()}</div>
                <div style="font-weight:bold;color:${margin>=30?'#10B981':margin>=15?'#F59E0B':'#EF4444'};">Margin: ${margin}% (₹${revenue.toLocaleString()}/mo)</div> <button class="btn btn-sm" onclick="event.stopPropagation(); editOnboarded(${r.id})" style="margin-top:4px;">✏️ Edit</button> <button class="btn btn-sm" onclick="event.stopPropagation(); generatePayslip(${r.id})" style="margin-top:4px;background:#C9A96E;color:#fff;">📄 Payslip</button></div>
            </div></div>`;
    }).join('');
}

async function loadDailyReport() {
    const date = document.getElementById('reportDate').value || new Date().toISOString().split('T')[0];
    const container = document.getElementById('dailyReportContent');
    container.innerHTML = '<div class="spinner"></div>';
    
    const res = await fetch('/api/daily-report?date=' + date);
    const data = await res.json();
    
    let html = `<h4>📅 Report for ${data.date}</h4>`;
    
    // Active Requirements
    html += `<div class="card" style="margin:10px 0;"><h4>📋 Active Requirements: ${data.active_requirements}</h4>`;
    if (data.active_jobs.length === 0) {
        html += '<p style="color:#999;">No active requirements</p>';
    } else {
        data.active_jobs.forEach(j => {
            html += `<div style="font-size:13px;padding:4px 0;">
                🔹 <a href="javascript:void(0)" onclick="showPanel('jobs'); setTimeout(() => loadJobs(), 300);" style="color:#1B2A4A;text-decoration:underline;">
                    ${escapeHtml(j.title)} - ${escapeHtml(j.requirement_id || 'SIT-R-'+String(j.id).padStart(3,'0'))}
                </a> (${escapeHtml(j.company||'N/A')})
            </div>`;
        });
    }
    html += `</div>`;
    
    // Proposals Sent
    html += `<div class="card" style="margin:10px 0;"><h4>📤 Profiles Proposed: ${data.candidates_added}</h4>`;
    if (data.candidates.length === 0) {
        html += '<p style="color:#999;">No profiles proposed on this date</p>';
    } else {
        data.candidates.forEach(c => {
            html += `<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #eee;">
                👤 <a href="javascript:void(0)" onclick="viewCandidate(${c.id})" style="color:#1B2A4A;text-decoration:underline;font-weight:bold;">
                    ${escapeHtml(c.first_name||'')} ${escapeHtml(c.last_name||'')}
                </a>
                | 🏢 ${escapeHtml(c.proposed_client||'N/A')} 
                | 📋 ${escapeHtml(c.proposed_requirement||'N/A')}
                | 👤 HR: ${escapeHtml(c.uploaded_by_name||'N/A')}
            </div>`;
        });
    }
    html += `</div>`;
    
    // Interviews Scheduled
    html += `<div class="card" style="margin:10px 0;"><h4>📅 Interviews Scheduled: ${data.interviews_scheduled}</h4>`;
    if (data.interviews.length === 0) {
        html += '<p style="color:#999;">No interviews scheduled on this date</p>';
    } else {
        data.interviews.forEach(i => {
            html += `<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #eee;">
                🕐 ${i.interview_time||'TBD'} - 
                <a href="javascript:void(0)" onclick="showPanel('interviews'); document.getElementById('intFilterDate').value='${i.interview_date}'; loadInterviews();" style="color:#1B2A4A;text-decoration:underline;font-weight:bold;">
                    ${escapeHtml(i.candidate_name)}
                </a> 
                (${escapeHtml(i.round)}) - 🏢 ${escapeHtml(i.client_name||'N/A')}
            </div>`;
        });
    }
    html += `</div>`;
    
    // Interviews Completed
    html += `<div class="card" style="margin:10px 0;"><h4>✅ Interviews Completed: ${data.interviews_completed}</h4>`;
    if (data.completed_interviews.length === 0) {
        html += '<p style="color:#999;">No interviews completed on this date</p>';
    } else {
        data.completed_interviews.forEach(i => {
            html += `<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #eee;">
                ${i.verdict} - 
                <a href="javascript:void(0)" onclick="showPanel('interviews'); document.getElementById('intFilterDate').value='${i.interview_date}'; loadInterviews();" style="color:#1B2A4A;text-decoration:underline;font-weight:bold;">
                    ${escapeHtml(i.candidate_name)}
                </a> 
                (${escapeHtml(i.round)}) - 🏢 ${escapeHtml(i.client_name||'N/A')}
            </div>`;
        });
    }
        // Proposals by Recruiter
    html += `<div class="card" style="margin:10px 0;"><h4>📊 Proposals by Recruiter</h4>`;
    if (data.proposals_by_recruiter && data.proposals_by_recruiter.length > 0) {
        data.proposals_by_recruiter.forEach(p => {
            html += `<div style="font-size:14px;padding:4px 0;border-bottom:1px solid #eee;">
                👤 <strong>${escapeHtml(p.uploaded_by_name || 'N/A')}</strong>: ${p.count} proposal(s)
            </div>`;
        });
    } else {
        html += '<p style="color:#999;">No proposals on this date</p>';
    }
    html += `</div>`;
       
    container.innerHTML = html;
}
async function loadKanban() {
    const res = await fetch('/api/candidates');
    const candidates = await res.json();
    const board = document.getElementById('kanbanBoard');
    
    board.innerHTML = kanbanStages.map(stage => {
        const stageCandidates = candidates.filter(c => (c.stage || 'new') === stage.id);
        return `
            <div style="background:#F5F7FA;border-radius:10px;min-height:150px;min-width:200px;max-width:240px;display:flex;flex-direction:column;flex-shrink:0;">
                <div style="background:${stage.color};color:#fff;padding:10px 14px;border-radius:10px 10px 0 0;font-weight:bold;font-size:13px;display:flex;justify-content:space-between;">
                    <span>${stage.emoji} ${stage.name}</span>
                    <span style="background:rgba(255,255,255,0.3);padding:2px 8px;border-radius:10px;font-size:11px;">${stageCandidates.length}</span>
                </div>
                <div style="padding:8px;flex:1;min-height:100px;" 
                     ondragover="event.preventDefault()" 
                     ondrop="dropCandidate(event, '${stage.id}')">
                    ${stageCandidates.map(c => `
                                                <div draggable="true" 
                             ondragstart="dragCandidate(event, ${c.id})" 
                             onclick="viewCandidate(${c.id})"
                             style="background:#fff;padding:8px;margin-bottom:5px;border-radius:6px;border-left:3px solid ${stage.color};cursor:pointer;font-size:11px;box-shadow:0 1px 2px rgba(0,0,0,0.08);">
                            <strong style="font-size:11px;">${escapeHtml(c.first_name || '')} ${escapeHtml(c.last_name || '')}</strong>
                            <div style="color:#666;font-size:10px;">${escapeHtml(c.designation || c.current_role || '')}</div>
                            ${c.match_score ? `<span style="background:${c.match_score>=70?'#10B981':c.match_score>=40?'#F59E0B':'#EF4444'};color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;">${c.match_score}%</span>` : ''}
                        </div>
                    `).join('')}
                    ${stageCandidates.length === 0 ? '<div style="color:#bbb;font-size:11px;text-align:center;padding:20px;">Drop here</div>' : ''}
                </div>
            </div>
        `;
    }).join('');
}

let draggedCandidateId = null;

function dragCandidate(event, candidateId) {
    draggedCandidateId = candidateId;
    event.dataTransfer.effectAllowed = 'move';
}

async function dropCandidate(event, stage) {
    event.preventDefault();
    if (!draggedCandidateId) return;
    
    await fetch('/api/candidates/' + draggedCandidateId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ stage: stage })
    });
    
    draggedCandidateId = null;
    loadKanban();
    toastSuccess('Stage updated!');
}
    
    function renderMatchChart(distribution) {
        const canvas = document.getElementById('matchChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
        const values = [
            distribution['0-20'] || 0,
            distribution['21-40'] || 0,
            distribution['41-60'] || 0,
            distribution['61-80'] || 0,
            distribution['81-100'] || 0
        ];
        const colors = ['#F44336', '#FF9800', '#FFC107', '#4CAF50', '#1B6B2E'];
        
        if (matchChartInstance) matchChartInstance.destroy();
        matchChartInstance = new Chart(ctx, {
            type: 'bar',
            data: { labels: labels, datasets: [{ label: 'Candidates', data: values, backgroundColor: colors, borderColor: colors, borderWidth: 1 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
    }
    
    function renderPipelineChart(pipeline) {
        const canvas = document.getElementById('pipelineChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = ['New', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected'];
        const values = [pipeline.new||0, pipeline.screening||0, pipeline.interview||0, pipeline.offer||0, pipeline.hired||0, pipeline.rejected||0];
        const colors = ['#2196F3', '#FF9800', '#FF5722', '#9C27B0', '#4CAF50', '#F44336'];
        if (values.every(v => v === 0)) return;
        if (pipelineChartInstance) pipelineChartInstance.destroy();
        pipelineChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderColor: '#fff', borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } } } }
        });
    }
    
   function renderSkillsCloud(skills) {
    const container = document.getElementById('skillsCloud');
    if (!container) return;
    if (!skills || skills.length === 0) { 
        container.innerHTML = '<p style="color: #999; font-style: italic;">No skills data available</p>'; 
        return; 
    }
    
    const normalizedSkills = skills.map(s => 
        typeof s === 'object' ? {skill: s.skill || s.name || '', count: s.count || 1} : {skill: String(s), count: 1}
    );
    const topSkills = normalizedSkills.slice(0, 15);
    const maxCount = topSkills[0]?.count || 1;
    
    container.innerHTML = topSkills.map(s => {
        const size = 12 + (s.count / maxCount) * 20;
        return '<span style="font-size:' + size + 'px; color:#1A4D4A; background:#F5F0E8; padding:4px 12px; border-radius:20px; border:1px solid #ddd; opacity:' + (0.6 + (s.count / maxCount) * 0.4) + ';">' + escapeHtml(s.skill) + '</span>';
    }).join('');
}
    
    function renderTrendChart(trend) {
        const canvas = document.getElementById('trendChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = trend.labels || [];
        const values = trend.values || [];
        if (trendChartInstance) trendChartInstance.destroy();
        if (labels.length === 0) return;
        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Candidates Added', data: values, borderColor: '#1A4D4A', backgroundColor: 'rgba(26,77,74,0.1)', fill: true, tension: 0.3, pointBackgroundColor: '#1A4D4A' }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
    }
    // ========== AI DEEP DIVE FROM BATCH RESULTS ==========
    window.runDeepAnalysis = async function(candidateId, jobTitle) {
        // Find the job by title
        const job = allJobs.find(j => j.title === jobTitle);
        if (!job) { 
            toastError('Job not found. Please select from Analyze tab.');
            return; 
        }
        
        const cand = allCandidates.find(c => c.id == candidateId);
        if (!cand) { 
            toastError('Candidate not found.');
            return; 
        }
        
        // Switch to analyze tab
        showPanel('analyze');
        
        // Wait for panel to show
        setTimeout(() => {
            // Set the job and candidate in the dropdowns
            document.getElementById('jobSelect').value = job.id;
            document.getElementById('candidateSelect').value = candidateId;
            
            // Trigger the analysis
            document.getElementById('analyzeBtn').click();
            
            // Scroll to analysis result after a delay
            setTimeout(() => {
                const resultDiv = document.getElementById('analysisResult');
                if (resultDiv) {
                    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 500);
        }, 300);
    };
    
    function updateStats() {
        const total = allCandidates.length;
        const matched = allCandidates.filter(c => (c.match_score || 0) >= 70).length;
        const hired = allCandidates.filter(c => c.employment_status === 'hired').length;
        const rejected = allCandidates.filter(c => c.employment_status === 'rejected').length;
        const screening = allCandidates.filter(c => c.employment_status === 'screening').length;
        const interview = allCandidates.filter(c => c.employment_status === 'interview').length;
        const offer = allCandidates.filter(c => c.employment_status === 'offer').length;
        const newCount = allCandidates.filter(c => c.employment_status === 'new' || !c.employment_status).length;
        
        document.getElementById('candidateStats').textContent = `📊 ${total} total  |  🎯 ${matched} matched  |  ✅ ${hired} hired  |  ❌ ${rejected} rejected`;
        
        // Update pipeline stats
        document.getElementById('stat-new-count').textContent = newCount;
        document.getElementById('stat-screening-count').textContent = screening;
        document.getElementById('stat-interview-count').textContent = interview;
        document.getElementById('stat-offer-count').textContent = offer;
        document.getElementById('stat-hired-count').textContent = hired;
        document.getElementById('stat-rejected-count').textContent = rejected;
        
        // Uploader stats
        renderUploaderStats();
    }

    function renderUploaderStats() {
        if (!Array.isArray(allCandidates)) return;
        const uploaderMap = {};
        allCandidates.forEach(c => {
            const uploader = c.uploaded_by || 'ShahnaIT';
            uploaderMap[uploader] = (uploaderMap[uploader] || 0) + 1;
        });
        
        const sorted = Object.entries(uploaderMap).sort((a, b) => b[1] - a[1]);
        const maxCount = sorted.length > 0 ? sorted[0][1] : 1;
        const total = allCandidates.length;
        
        const container = document.getElementById('uploaderChart');
        if (sorted.length === 0) {
            container.innerHTML = '<p style="color: #999; font-style: italic;">No candidates uploaded yet</p>';
            return;
        }
        
        container.innerHTML = sorted.map(([name, count]) => {
            const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
            const barWidth = Math.max(5, Math.round((count / maxCount) * 100));
            return `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="min-width: 120px; font-size: 13px; font-weight: 500;">👤 ${escapeHtml(name)}</span>
                    <div style="flex: 1; background: #F0F0F0; border-radius: 10px; height: 22px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #1A4D4A, #2A6B67); height: 100%; width: ${barWidth}%; border-radius: 10px; transition: width 0.5s; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 11px; font-weight: bold;">${count}</div>
                    </div>
                    <span style="min-width: 60px; font-size: 13px; color: #666; text-align: right;">${percentage}%</span>
                </div>
            `;
        }).join('');
    }
    function escapeHtml(str) { 
    if (!str) return ''; 
    // Convert to string if it's not already
    str = String(str);
    return str.replace(/[&<>]/g, function(m) { 
        if(m==='&') return '&amp;'; 
        if(m==='<') return '&lt;'; 
        if(m==='>') return '&gt;'; 
        return m; 
    }); 
}

// ============================================
// PROPOSAL REPORTS (Master Reporting Engine)
// ============================================
const rpState = { range: 'day', loaded: false };
const rpEl = (id) => document.getElementById(id);

function rpIsoToday() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function rpSetRange(range) {
    rpState.range = range;
    document.querySelectorAll('#rpRangeSeg button').forEach((b) => b.classList.toggle('active', b.dataset.range === range));
    const custom = range === 'custom';
    rpEl('rpDateWrap').style.display = custom ? 'none' : '';
    rpEl('rpStartWrap').style.display = custom ? '' : 'none';
    rpEl('rpEndWrap').style.display = custom ? '' : 'none';
}

function rpParams(format) {
    const p = new URLSearchParams({ range: rpState.range, format: format || 'json' });
    if (rpState.range === 'custom') { p.set('start', rpEl('rpStart').value); p.set('end', rpEl('rpEnd').value); }
    else p.set('date', rpEl('rpDate').value);
    const hr = rpEl('rpHr').value.trim(), skill = rpEl('rpSkill').value.trim(), client = rpEl('rpClient').value.trim();
    if (hr) p.set('hr', hr);
    if (skill) p.set('skill', skill);
    if (client) p.set('client', client);
    return p.toString();
}

async function rpOpen() {
    if (!rpEl('rpDate').value) rpEl('rpDate').value = rpIsoToday();
    if (!rpEl('rpStart').value) rpEl('rpStart').value = rpEl('rpEnd').value = rpIsoToday();
    if (!rpState.loaded) {
        rpState.loaded = true;
        document.querySelectorAll('#rpRangeSeg button').forEach((b) => b.addEventListener('click', () => { rpSetRange(b.dataset.range); rpLoad(); }));
        ['rpDate', 'rpStart', 'rpEnd'].forEach((id) => rpEl(id).addEventListener('change', rpLoad));
        ['rpHr', 'rpSkill', 'rpClient'].forEach((id) => rpEl(id).addEventListener('keydown', (e) => { if (e.key === 'Enter') rpLoad(); }));
        try {
            const res = await fetch('/api/reports/filter-options', { credentials: 'same-origin' });
            if (res.ok) {
                const o = await res.json();
                const fill = (id, list) => { rpEl(id).innerHTML = ''; (list || []).forEach((v) => { const op = document.createElement('option'); op.value = v; rpEl(id).appendChild(op); }); };
                fill('rpHrList', o.hr); fill('rpClientList', o.clients);
                rpEl('rpHrWrap').style.display = o.see_all ? '' : 'none';    // recruiters only ever see their own proposals
            }
        } catch (e) { /* the datalists are optional */ }
    }
    rpLoad();
}

function rpReset() {
    rpSetRange('day');
    rpEl('rpDate').value = rpEl('rpStart').value = rpEl('rpEnd').value = rpIsoToday();
    rpEl('rpHr').value = rpEl('rpSkill').value = rpEl('rpClient').value = '';
    rpLoad();
}

async function rpLoad() {
    const summary = rpEl('rpSummary'), table = rpEl('rpTable');
    summary.textContent = 'Loading…';
    try {
        const res = await fetch('/api/reports/proposals?' + rpParams('json'), { credentials: 'same-origin' });
        const j = await res.json().catch(() => ({}));
        if (!res.ok) { summary.textContent = ''; table.innerHTML = ''; showToast(j.error || 'Could not load the report', 'error'); return; }
        summary.textContent = j.range.label + '  ·  ' + j.count + ' proposal' + (j.count === 1 ? '' : 's') + (j.truncated ? '  (first 5000 shown)' : '');
        table.textContent = '';
        const thead = table.createTHead().insertRow();
        j.columns.forEach((c) => { const th = document.createElement('th'); th.textContent = c; thead.appendChild(th); });
        const body = table.createTBody();
        if (!j.rows.length) {
            const td = body.insertRow().insertCell(); td.colSpan = j.columns.length; td.className = 'rp-empty';
            td.textContent = '📭 No proposals found for these filters.';
            return;
        }
        const labels = {}; j.groups.forEach((g) => { labels[g.date] = g.label + '  -  ' + g.count + ' proposal' + (g.count === 1 ? '' : 's'); });
        let last = null;
        j.rows.forEach((r) => {
            if (r._date !== last) {
                last = r._date;
                const td = body.insertRow().insertCell(); td.colSpan = j.columns.length; td.className = 'rp-band'; td.textContent = labels[last] || last;
            }
            const tr = body.insertRow();
            j.columns.forEach((c) => { tr.insertCell().textContent = r[c] || ''; });     // textContent: tracker values are never rendered as HTML
        });
    } catch (e) {
        summary.textContent = '';
        showToast('Network error while loading the report', 'error');
    }
}

async function rpDownload(format) {
    const btn = rpEl(format === 'xlsx' ? 'rpXlsxBtn' : 'rpPdfBtn');
    const label = btn.textContent; btn.disabled = true; btn.textContent = 'Preparing…';
    try {
        const res = await fetch('/api/reports/proposals?' + rpParams(format), { credentials: 'same-origin' });
        if (!res.ok) { const j = await res.json().catch(() => ({})); showToast(j.error || 'Download failed', 'error'); return; }
        const blob = await res.blob();
        const m = /filename="?([^";]+)"?/.exec(res.headers.get('Content-Disposition') || '');
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = m ? m[1] : 'Proposals.' + format;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (e) {
        showToast('Network error while downloading', 'error');
    } finally {
        btn.disabled = false; btn.textContent = label;
    }
}

const tabProposalReports = document.getElementById('tabProposalReports');
if (tabProposalReports) tabProposalReports.onclick = function () { showPanel('proposalReports'); rpOpen(); };
