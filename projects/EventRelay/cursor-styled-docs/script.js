// Navigation functionality
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const sections = document.querySelectorAll('.content-section');

    function showSection(sectionId) {
        sections.forEach(section => {
            section.style.display = section.id === sectionId ? 'block' : 'none';
        });

        // Update active states
        navLinks.forEach(link => {
            const href = link.getAttribute('href').substring(1);
            link.classList.toggle('active', href === sectionId);
        });

        sidebarLinks.forEach(link => {
            const href = link.getAttribute('href').substring(1);
            link.classList.toggle('active', href === sectionId);
        });

        // Update URL hash
        window.location.hash = sectionId;
    }

    // Handle navigation clicks
    [...navLinks, ...sidebarLinks].forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.getAttribute('href').substring(1);
            showSection(sectionId);
        });
    });

    // Handle initial load and hash changes
    function handleHashChange() {
        const hash = window.location.hash.substring(1);
        const targetSection = hash || 'quickstart';
        showSection(targetSection);
    }

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
}

// Search functionality
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.toLowerCase();

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    function performSearch(query) {
        if (!query) {
            clearSearchHighlights();
            return;
        }

        const sections = document.querySelectorAll('.content-section');
        sections.forEach(section => {
            const text = section.textContent.toLowerCase();
            const hasMatch = text.includes(query);
            
            // Highlight matching sections
            if (hasMatch) {
                highlightMatches(section, query);
            } else {
                clearHighlights(section);
            }
        });
    }

    function highlightMatches(element, query) {
        // Simple highlight implementation
        // In production, use a more sophisticated highlighting library
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }

        textNodes.forEach(textNode => {
            const text = textNode.textContent;
            const regex = new RegExp(`(${query})`, 'gi');
            if (regex.test(text)) {
                const span = document.createElement('span');
                span.innerHTML = text.replace(regex, '<mark>$1</mark>');
                textNode.parentNode.replaceChild(span, textNode);
            }
        });
    }

    function clearSearchHighlights() {
        document.querySelectorAll('mark').forEach(mark => {
            const parent = mark.parentNode;
            parent.replaceChild(document.createTextNode(mark.textContent), mark);
            parent.normalize();
        });
    }

    function clearHighlights(element) {
        element.querySelectorAll('mark').forEach(mark => {
            const parent = mark.parentNode;
            parent.replaceChild(document.createTextNode(mark.textContent), mark);
            parent.normalize();
        });
    }
}

// Copy code functionality
function initCodeCopy() {
    document.addEventListener('click', (e) => {
        if (e.target.closest('.copy-btn')) {
            const button = e.target.closest('.copy-btn');
            copyCode(button);
        }
    });
}

function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    const code = codeBlock.querySelector('code').textContent;

    navigator.clipboard.writeText(code).then(() => {
        // Show success state
        button.classList.add('copied');
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';

        setTimeout(() => {
            button.classList.remove('copied');
            button.innerHTML = originalHTML;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code:', err);
    });
}

// Video filtering
function initVideoFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const videoCards = document.querySelectorAll('.video-card');

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            const filter = button.getAttribute('data-filter');
            
            // Update active button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Filter videos
            videoCards.forEach(card => {
                const category = card.getAttribute('data-category');
                if (filter === 'all' || category === filter) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
}

// Smooth scroll for anchor links
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target && !this.classList.contains('nav-link') && !this.classList.contains('sidebar-link')) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Mobile sidebar toggle
function initMobileSidebar() {
    const sidebar = document.querySelector('.sidebar');
    let startX = null;
    let currentX = null;

    // Touch events for swipe to open/close sidebar
    document.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
    });

    document.addEventListener('touchmove', (e) => {
        if (!startX) return;
        currentX = e.touches[0].clientX;
    });

    document.addEventListener('touchend', () => {
        if (!startX || !currentX) return;
        
        const diffX = currentX - startX;
        
        // Swipe right to open
        if (diffX > 50 && startX < 50) {
            sidebar.classList.add('open');
        }
        
        // Swipe left to close
        if (diffX < -50) {
            sidebar.classList.remove('open');
        }
        
        startX = null;
        currentX = null;
    });

    // Click outside to close
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 1024 && 
            !sidebar.contains(e.target) && 
            sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    });
}

// Initialize all features when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initSearch();
    initCodeCopy();
    initVideoFilters();
    initSmoothScroll();
    initMobileSidebar();

    // Initialize Prism for syntax highlighting
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
});

// Export functions for external use
window.copyCode = copyCode; 