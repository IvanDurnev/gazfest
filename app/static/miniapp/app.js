const webApp = window.WebApp;

if (webApp) {
  webApp.ready?.();
  webApp.expand?.();

  const firstName = webApp.initDataUnsafe?.user?.first_name;
  if (firstName) {
    document.querySelector("#assistant-greeting").textContent =
      `Привет, ${firstName}! Я Геля 👋 Чем тебе помочь?`;
  }
}

window.lucide?.createIcons();

const toast = document.querySelector("#toast");
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 2200);
}

document.querySelectorAll("[data-toast]").forEach((button) => {
  button.addEventListener("click", () => {
    showToast(button.dataset.toast);
  });
});

document.querySelectorAll("[data-section]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(`#${button.dataset.section}`)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  });
});

document.querySelectorAll(".favorite").forEach((button) => {
  button.addEventListener("click", () => {
    const isActive = button.classList.toggle("is-active");
    button.setAttribute("aria-pressed", String(isActive));
    showToast(isActive ? "Добавлено в избранное" : "Удалено из избранного");
  });
});

const showAll = document.querySelector("#show-all");
const extraEvents = document.querySelectorAll(".schedule-row--extra");

showAll.addEventListener("click", () => {
  const willShow = extraEvents[0].hidden;
  extraEvents.forEach((event) => {
    event.hidden = !willShow;
  });
  showAll.firstChild.textContent = willShow ? "Свернуть " : "Смотреть все ";
  window.lucide?.createIcons();
});

const applicationButton = document.querySelector("#open-application");
const applicationsOverview = document.querySelector(
  "#applications-overview",
);
const applicationsCount = document.querySelector("#applications-count");
const applicationsList = document.querySelector("#applications-list");
const applicationSheet = document.querySelector("#application-sheet");
const applicationBackdrop = document.querySelector("#application-backdrop");
const applicationClose = document.querySelector("#close-application");
const applicationDone = document.querySelector("#application-done");
const applicationForm = document.querySelector("#application-form");
const applicationSuccess = document.querySelector("#application-success");
const applicationError = document.querySelector("#application-error");
const applicationSubmit = document.querySelector("#application-submit");
const rideFields = document.querySelector("#ride-fields");
const starsFields = document.querySelector("#stars-fields");
const alreadyApplied = document.querySelector("#already-applied");
let savedApplications = [];
let applicationSubmitting = false;

const equipmentLabels = {
  bicycle: "Велосипед",
  rollers: "Ролики",
  scooter: "Самокат",
  // Legacy labels are retained for applications submitted before this change.
  skate: "Скейт",
  other: "Другой снаряд",
};

function createIcon(name) {
  const icon = document.createElement("i");
  icon.dataset.lucide = name;
  return icon;
}

function formatAge(age) {
  const remainder100 = age % 100;
  const remainder10 = age % 10;
  if (remainder100 >= 11 && remainder100 <= 14) {
    return `${age} лет`;
  }
  if (remainder10 === 1) {
    return `${age} год`;
  }
  if (remainder10 >= 2 && remainder10 <= 4) {
    return `${age} года`;
  }
  return `${age} лет`;
}

function applicationDetails(application) {
  const fullName = `${application.first_name} ${application.last_name}`;
  if (application.activity === "ride") {
    const equipment =
      application.equipment === "other"
        ? application.equipment_other
        : equipmentLabels[application.equipment];
    return `${fullName} · ${formatAge(application.age)} · ${equipment}`;
  }
  return `${fullName} · ${application.phone}`;
}

function renderApplications() {
  applicationsList.replaceChildren();
  applicationsCount.textContent = String(savedApplications.length);
  applicationsOverview.hidden = savedApplications.length === 0;

  savedApplications.forEach((application) => {
    const card = document.createElement("article");
    card.className = `saved-application saved-application--${application.activity}`;

    const icon = document.createElement("span");
    icon.className = "saved-application__icon";
    icon.append(
      createIcon(application.activity === "ride" ? "bike" : "mic-vocal"),
    );

    const copy = document.createElement("span");
    copy.className = "saved-application__copy";
    const title = document.createElement("strong");
    title.textContent =
      application.activity === "ride"
        ? "Участие в заезде"
        : "Шоу «Время звезд»";
    const details = document.createElement("small");
    details.textContent = applicationDetails(application);
    copy.append(title, details);

    const status = document.createElement("span");
    status.className = "saved-application__status";
    status.append(createIcon("circle-check"));
    const statusText = document.createElement("span");
    statusText.textContent = "Отправлена";
    status.append(statusText);

    card.append(icon, copy, status);
    applicationsList.append(card);
  });

  window.lucide?.createIcons();
}

async function loadApplications() {
  if (!webApp?.initData) {
    return;
  }

  try {
    const response = await fetch("/max/miniapp/applications", {
      headers: {"X-Max-WebApp-Data": webApp.initData},
    });
    if (!response.ok) {
      return;
    }
    const result = await response.json();
    savedApplications = result.applications || [];
    renderApplications();
    syncSelectedApplicationState();
  } catch {
    // The form remains available; submission will show a detailed API error.
  }
}

function setRequired(container, selector, required) {
  container.querySelectorAll(selector).forEach((field) => {
    field.required = required;
  });
}

function updateActivityFields() {
  const activity = new FormData(applicationForm).get("activity");
  const isRide = activity === "ride";

  rideFields.hidden = !isRide;
  starsFields.hidden = isRide;
  setRequired(rideFields, "[name='age']", isRide);
  setRequired(starsFields, "[name='phone']", !isRide);
  setRequired(starsFields, "[name='performance_description']", !isRide);
  syncSelectedApplicationState();
}

function syncSelectedApplicationState() {
  const activity = new FormData(applicationForm).get("activity");
  const alreadyExists = savedApplications.some(
    (application) => application.activity === activity,
  );

  alreadyApplied.hidden = !alreadyExists;
  applicationSubmit.disabled = applicationSubmitting || alreadyExists;
  applicationSubmit.querySelector("span").textContent = applicationSubmitting
    ? "Отправляем…"
    : alreadyExists
      ? "Заявка уже подана"
      : "Отправить заявку";
}

function openApplication() {
  applicationSheet.hidden = false;
  applicationBackdrop.hidden = false;
  document.body.classList.add("sheet-open");

  const user = webApp?.initDataUnsafe?.user;
  if (user) {
    const firstNameInput = document.querySelector("#application-first-name");
    const lastNameInput = document.querySelector("#application-last-name");
    if (!firstNameInput.value) {
      firstNameInput.value = user.first_name || "";
    }
    if (!lastNameInput.value) {
      lastNameInput.value = user.last_name || "";
    }
  }

  if (savedApplications.length === 1) {
    const availableActivity =
      savedApplications[0].activity === "ride" ? "stars" : "ride";
    applicationForm.querySelector(
      `[name="activity"][value="${availableActivity}"]`,
    ).checked = true;
  }

  updateActivityFields();
  applicationClose.focus();
}

function closeApplication() {
  applicationSheet.hidden = true;
  applicationBackdrop.hidden = true;
  document.body.classList.remove("sheet-open");
  applicationError.hidden = true;

  if (!applicationSuccess.hidden) {
    applicationSuccess.hidden = true;
    applicationForm.hidden = false;
    applicationForm.reset();
    updateActivityFields();
  }

  applicationButton.focus();
}

applicationButton.addEventListener("click", openApplication);
applicationClose.addEventListener("click", closeApplication);
applicationDone.addEventListener("click", closeApplication);
applicationBackdrop.addEventListener("click", closeApplication);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !applicationSheet.hidden) {
    closeApplication();
  }
});

applicationForm
  .querySelectorAll("[name='activity']")
  .forEach((input) => input.addEventListener("change", updateActivityFields));

applicationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  applicationError.hidden = true;

  if (!applicationForm.reportValidity()) {
    return;
  }

  if (!webApp?.initData) {
    applicationError.textContent =
      "Откройте мини-приложение через бот в MAX, чтобы отправить заявку.";
    applicationError.hidden = false;
    return;
  }

  const formData = new FormData(applicationForm);
  const activity = formData.get("activity");
  const payload = {
    activity,
    first_name: formData.get("first_name"),
    last_name: formData.get("last_name"),
  };

  if (activity === "ride") {
    payload.age = Number(formData.get("age"));
    payload.equipment = formData.get("equipment");
  } else {
    payload.phone = formData.get("phone");
    payload.performance_description = formData.get(
      "performance_description",
    );
  }

  applicationSubmitting = true;
  syncSelectedApplicationState();

  try {
    const response = await fetch("/max/miniapp/applications", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Max-WebApp-Data": webApp.initData,
      },
      body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || "Не удалось отправить заявку.");
    }

    await loadApplications();
    applicationForm.hidden = true;
    applicationSuccess.hidden = false;
    applicationSheet.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    applicationError.textContent =
      error.message || "Не удалось отправить заявку. Попробуйте ещё раз.";
    applicationError.hidden = false;
    applicationError.scrollIntoView({ behavior: "smooth", block: "center" });
  } finally {
    applicationSubmitting = false;
    syncSelectedApplicationState();
  }
});

updateActivityFields();
loadApplications();
