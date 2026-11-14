// Code Black interactions: accessible menu, scroll reveals, progress and forms.
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const menuButton = document.querySelector("#menuButton");
const nav = document.querySelector("#siteNav");

if (menuButton && nav) {
  menuButton.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  });
  nav.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
    nav.classList.remove("is-open");
    menuButton.setAttribute("aria-expanded", "false");
  }));
}

const year = document.querySelector("#year");
if (year) year.textContent = new Date().getFullYear();

const progress = document.querySelector("#readingProgress");
function updateProgress() {
  if (!progress) return;
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const amount = max > 0 ? (window.scrollY / max) * 100 : 0;
  progress.style.width = `${Math.min(100, Math.max(0, amount))}%`;
}
window.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();

const revealItems = document.querySelectorAll(".reveal");
if (!reduceMotion && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -35px 0px" });
  revealItems.forEach(item => observer.observe(item));
} else {
  revealItems.forEach(item => item.classList.add("is-visible"));
}

const select = document.querySelector("#serviceSelect");
if (select) {
  const requested = new URLSearchParams(window.location.search).get("service");
  if (requested) {
    const option = [...select.options].find(item => item.text.trim().toLowerCase() === requested.trim().toLowerCase());
    if (option) select.value = option.value;
  }
}

async function wireForm(formId, endpoint, messageId) {
  const form = document.getElementById(formId);
  const message = document.getElementById(messageId);
  if (!form || !message) return;
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const submit = form.querySelector('button[type="submit"]');
    const original = submit.textContent;
    submit.disabled = true;
    submit.textContent = "Sending…";
    message.textContent = "Sending your details securely…";
    message.className = "form-message";
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || "Please check your details and try again.");
      message.textContent = result.message;
      message.classList.add("success");
      form.reset();
    } catch (error) {
      message.textContent = error.message || "Something went wrong. Please try again later.";
      message.classList.add("error");
    } finally {
      submit.disabled = false;
      submit.textContent = original;
    }
  });
}
wireForm("enquiryForm", "/api/enquiries", "enquiryMessage");
wireForm("applicationForm", "/api/applications", "applicationMessage");

// --- SCANNER LOGIC ---
const scanBtn = document.getElementById("scanBtn");
const scanUrlInput = document.getElementById("scanUrl");
const scanResult = document.getElementById("scanResult");

if (scanBtn) {
    scanBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        const url = scanUrlInput.value.trim();
        if (!url) return alert("Please enter a URL");

        scanResult.innerHTML = "Scanning... Please wait...";
        
        try {
            const response = await fetch("/api/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url })
            });
            const res = await response.json();
            
            if (res.ok) {
                const data = res.data;
                if (data.error) {
                    scanResult.innerHTML = `<span style="color:red;">Error: ${data.error}</span>`;
                } else {
                    // Pehle basic result dikhao
                    scanResult.innerHTML = `
                        <strong>[HTTPS]:</strong> ${data.https ? "✅ Enabled" : "❌ Not Enabled"} <br>
                        <strong>[Missing Headers]:</strong> ${data.missing_headers.length > 0 ? "❌ " + data.missing_headers.join(", ") : "✅ All Present"} <br>
                        <strong>[Open Ports]:</strong> ${data.open_ports.length > 0 ? data.open_ports.join(", ") : "None"}
                    `;

                    // Phir PDF Download button add karo (Yahan hona chahiye!)
                    const downloadLink = `/api/download_report?url=${encodeURIComponent(url)}&https=${data.https}&missing_headers=${data.missing_headers.join(',')}`;

                    scanResult.innerHTML += `
                        <br><br>
                        <a href="${downloadLink}" target="_blank" class="button button-light" style="display: inline-block; padding: 10px 20px; text-decoration: none; font-size: 12px;">📄 Download Full PDF Report</a>
                    `;
                }
            }
        } catch (err) {
            scanResult.innerHTML = "<span style='color:red;'>Something went wrong! Check server.</span>";
        }
    });
}