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

        scanResult.innerHTML = "<span style='color: #9be4df;'>Scanning... Please wait...</span>";
        
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
                    scanResult.innerHTML = `<span style="color:#FF4D4D;">Error: ${data.error}</span>`;
                } else {
                    // Naya Premium Result Format
                    scanResult.innerHTML = `
                        <div style="background: #0d131b; border: 1px solid #1e2a36; padding: 15px; border-radius: 6px; margin-top: 10px; width: 100%; max-width: 500px; font-family: monospace;">
                            <div style="margin-bottom: 5px;"><strong style="color: #9be4df;">[HTTPS]:</strong> ${data.https ? "✅ Enabled" : "❌ Not Enabled"}</div>
                            <div style="margin-bottom: 5px;"><strong style="color: #9be4df;">[Missing Headers]:</strong> ${data.missing_headers.length > 0 ? "❌ " + data.missing_headers.join(", ") : "✅ All Present"}</div>
                            <div style="margin-bottom: 5px;"><strong style="color: #9be4df;">[Open Ports]:</strong> ${data.open_ports.length > 0 ? data.open_ports.join(", ") : "None"}</div>
                            <div style="margin-bottom: 5px;"><strong style="color: #9be4df;">[SSL Expiry]:</strong> ${data.ssl_days_left > 0 ? data.ssl_days_left + " days left" : "Not Found"}</div>
                            <div style="margin-bottom: 5px;"><strong style="color: #9be4df;">[DNS A Record]:</strong> ${data.dns_a !== "N/A" ? data.dns_a : "Not Found"}</div>
                        </div>
                    `;

                    // UPDATE: Naye variables ke saath download link
                    const downloadLink = `/api/download_report?url=${encodeURIComponent(url)}&https=${data.https}&missing_headers=${data.missing_headers.join(',')}&ssl_days=${data.ssl_days_left}&dns_a=${encodeURIComponent(data.dns_a)}&dns_mx=${encodeURIComponent(data.dns_mx)}`;

                    scanResult.innerHTML += `
                        <br>
                        <a href="${downloadLink}" target="_blank" class="button button-light" style="display: inline-block; padding: 12px 20px; text-decoration: none; font-size: 14px; border-radius: 4px;">📄 Download Full PDF Report</a>
                    `;
                }
            }
        } catch (err) {
            scanResult.innerHTML = "<span style='color:#FF4D4D;'>Something went wrong! Check server.</span>";
        }
    });
}