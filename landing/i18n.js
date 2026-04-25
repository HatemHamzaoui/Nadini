/**
 * Nadini Landing Page — i18n (DE / EN / FR)
 */
const translations = {
  de: {
    // Nav
    "nav.features": "Funktionen",
    "nav.how": "So funktioniert's",
    "nav.compliance": "Compliance",
    "nav.pricing": "Preise",
    "nav.cta": "Jetzt starten",

    // Hero
    "hero.badge": "KI-gestützte Echtzeit-Übersetzung",
    "hero.title": "Sprache verbindet.<br>Nadini übersetzt.",
    "hero.subtitle": "Echtzeit-KI-Dolmetschen für Meetings, Konferenzen und Business-Kommunikation — mehrsprachig, sicher, AI-Act-konform.",
    "hero.cta_primary": "Kostenlos testen",
    "hero.cta_secondary": "Demo ansehen",
    "hero.trust": "Vertraut von über 200 Unternehmen in Europa",
    "hero.demo_live": "Live — 120 ms Latenz",

    // Features
    "features.label": "Funktionen",
    "features.title": "Alles, was Ihre mehrsprachige Kommunikation braucht",
    "features.subtitle": "Nadini vereint modernste KI-Modelle mit einer sicheren, europäischen Infrastruktur.",
    "features.f1.title": "Echtzeit-Übersetzung",
    "features.f1.desc": "Simultandolmetschen mit unter 200 ms Latenz. Sprechen Sie, während Ihre Teilnehmer in ihrer Sprache mithören.",
    "features.f2.title": "DSGVO & AI Act",
    "features.f2.desc": "Vollständig konform mit der EU-DSGVO und dem AI Act Art. 50. Transparenz-Disclosures, Audit-Logs, Datenhoheit in der EU.",
    "features.f3.title": "Unbegrenzte Teilnehmer",
    "features.f3.desc": "Meetings, Konferenzen, Webinare — egal ob 2 oder 2.000 Teilnehmer. Skaliert automatisch mit Ihrem Bedarf.",
    "features.f4.title": "30+ Sprachen",
    "features.f4.desc": "Von Deutsch und Englisch bis Arabisch, Mandarin und Japanisch. Ständig wachsende Sprachunterstützung durch mehrere KI-Modelle.",
    "features.f5.title": "Passwortlose Anmeldung",
    "features.f5.desc": "Magic-Link-Login per E-Mail — kein Passwort nötig. Sicher durch RS256-JWT, Token-Rotation und automatische Sperre.",
    "features.f6.title": "API & Integration",
    "features.f6.desc": "RESTful API, WebSocket-Streaming, JWKS-Endpunkt. Integrieren Sie Nadini nahtlos in Ihre bestehende Infrastruktur.",

    // How it works
    "how.label": "So funktioniert's",
    "how.title": "In drei Schritten zum mehrsprachigen Meeting",
    "how.s1.title": "Anmelden per Magic Link",
    "how.s1.desc": "Geben Sie Ihre E-Mail-Adresse ein und klicken Sie den Link in Ihrem Postfach. Kein Passwort, kein Aufwand.",
    "how.s2.title": "Meeting starten",
    "how.s2.desc": "Erstellen Sie ein Meeting und laden Sie Teilnehmer ein. Jeder wählt seine bevorzugte Sprache.",
    "how.s3.title": "Sprechen & verstehen",
    "how.s3.desc": "Sprechen Sie frei — Nadini übersetzt in Echtzeit für alle Teilnehmer. Transkript inklusive.",

    // Compliance
    "compliance.label": "Vertrauen & Compliance",
    "compliance.title": "Gebaut für europäische Standards",
    "compliance.subtitle": "Nadini erfüllt die strengsten regulatorischen Anforderungen — by design, nicht als Nachgedanke.",
    "compliance.c1.desc": "Transparente KI-Disclosure mit versionierten Texten, Pflichtbestätigung und dauerhafter Archivierung.",
    "compliance.c2.desc": "Datenverarbeitung in der EU. Auftragsverarbeitungsverträge, Löschfristen, Audit-Rechte — alles geregelt.",
    "compliance.c3.title": "Audit-Logging",
    "compliance.c3.desc": "Kategorisierte Audit-Logs mit konfigurierbarer Aufbewahrung. Compliance-Logs permanent, Standardlogs regelbasiert.",
    "compliance.c4.title": "Hybrid-Risk-Tier",
    "compliance.c4.desc": "Standard- und Hochrisiko-Tenants mit getrennten Compliance-Anforderungen. Nahtlose Eskalation ohne Architekturbruch.",
    "compliance.status.done": "Implementiert",
    "compliance.status.ready": "Bereit",

    // Pricing
    "pricing.label": "Preise",
    "pricing.title": "Transparent und fair",
    "pricing.subtitle": "Starten Sie kostenlos, skalieren Sie nach Bedarf.",
    "pricing.period": "/Monat",
    "pricing.popular": "Beliebt",
    "pricing.free.name": "Starter",
    "pricing.free.f1": "5 Stunden/Monat",
    "pricing.free.f2": "Bis zu 5 Teilnehmer",
    "pricing.free.f3": "10 Sprachen",
    "pricing.free.f4": "Standard-Support",
    "pricing.free.cta": "Kostenlos starten",
    "pricing.pro.name": "Business",
    "pricing.pro.f1": "Unbegrenzte Stunden",
    "pricing.pro.f2": "Unbegrenzte Teilnehmer",
    "pricing.pro.f3": "30+ Sprachen",
    "pricing.pro.f4": "API-Zugang",
    "pricing.pro.f5": "Prioritäts-Support",
    "pricing.pro.cta": "Business wählen",
    "pricing.ent.name": "Enterprise",
    "pricing.ent.amount": "Individuell",
    "pricing.ent.f1": "Alles aus Business",
    "pricing.ent.f2": "Hochrisiko-Compliance",
    "pricing.ent.f3": "Dedizierte Infrastruktur",
    "pricing.ent.f4": "SLA & Onboarding",
    "pricing.ent.f5": "AVV & FRIA-Support",
    "pricing.ent.cta": "Kontakt aufnehmen",

    // CTA
    "cta.title": "Bereit für mehrsprachige Meetings?",
    "cta.subtitle": "Starten Sie jetzt kostenlos — kein Passwort, keine Kreditkarte, keine Verpflichtung.",
    "cta.placeholder": "ihre@email.de",
    "cta.button": "Magic Link senden",
    "cta.hint": "Wir senden Ihnen einen Anmeldelink per E-Mail. Kein Passwort nötig.",

    // Footer
    "footer.desc": "KI-Echtzeit-Dolmetschen für die vernetzte Welt. Sicher, konform, europäisch.",
    "footer.product": "Produkt",
    "footer.docs": "Dokumentation",
    "footer.api": "API-Referenz",
    "footer.legal": "Rechtliches",
    "footer.privacy": "Datenschutz",
    "footer.imprint": "Impressum",
    "footer.terms": "AGB",
    "footer.aup": "Nutzungsrichtlinien",
    "footer.company": "Unternehmen",
    "footer.about": "Über uns",
    "footer.contact": "Kontakt",
    "footer.blog": "Blog",
    "footer.rights": "Alle Rechte vorbehalten.",
  },

  en: {
    "nav.features": "Features",
    "nav.how": "How it works",
    "nav.compliance": "Compliance",
    "nav.pricing": "Pricing",
    "nav.cta": "Get started",

    "hero.badge": "AI-powered real-time translation",
    "hero.title": "Language connects.<br>Nadini translates.",
    "hero.subtitle": "Real-time AI interpreting for meetings, conferences, and business communication — multilingual, secure, AI Act compliant.",
    "hero.cta_primary": "Try for free",
    "hero.cta_secondary": "Watch demo",
    "hero.trust": "Trusted by over 200 companies across Europe",
    "hero.demo_live": "Live — 120 ms latency",

    "features.label": "Features",
    "features.title": "Everything your multilingual communication needs",
    "features.subtitle": "Nadini combines cutting-edge AI models with a secure, European infrastructure.",
    "features.f1.title": "Real-time translation",
    "features.f1.desc": "Simultaneous interpreting with under 200 ms latency. Speak while your participants listen in their own language.",
    "features.f2.title": "GDPR & AI Act",
    "features.f2.desc": "Fully compliant with EU GDPR and AI Act Art. 50. Transparency disclosures, audit logs, data sovereignty in the EU.",
    "features.f3.title": "Unlimited participants",
    "features.f3.desc": "Meetings, conferences, webinars — whether 2 or 2,000 participants. Scales automatically with your needs.",
    "features.f4.title": "30+ languages",
    "features.f4.desc": "From German and English to Arabic, Mandarin, and Japanese. Constantly growing language support through multiple AI models.",
    "features.f5.title": "Passwordless login",
    "features.f5.desc": "Magic link login via email — no password needed. Secured by RS256 JWT, token rotation, and automatic lockout.",
    "features.f6.title": "API & integration",
    "features.f6.desc": "RESTful API, WebSocket streaming, JWKS endpoint. Integrate Nadini seamlessly into your existing infrastructure.",

    "how.label": "How it works",
    "how.title": "Three steps to multilingual meetings",
    "how.s1.title": "Sign in via Magic Link",
    "how.s1.desc": "Enter your email address and click the link in your inbox. No password, no hassle.",
    "how.s2.title": "Start a meeting",
    "how.s2.desc": "Create a meeting and invite participants. Everyone selects their preferred language.",
    "how.s3.title": "Speak & understand",
    "how.s3.desc": "Speak freely — Nadini translates in real time for all participants. Transcript included.",

    "compliance.label": "Trust & Compliance",
    "compliance.title": "Built for European standards",
    "compliance.subtitle": "Nadini meets the strictest regulatory requirements — by design, not as an afterthought.",
    "compliance.c1.desc": "Transparent AI disclosure with versioned texts, mandatory acknowledgment, and permanent archiving.",
    "compliance.c2.desc": "Data processing in the EU. Data processing agreements, deletion deadlines, audit rights — all covered.",
    "compliance.c3.title": "Audit logging",
    "compliance.c3.desc": "Categorized audit logs with configurable retention. Compliance logs permanent, standard logs rule-based.",
    "compliance.c4.title": "Hybrid risk tier",
    "compliance.c4.desc": "Standard and high-risk tenants with separate compliance requirements. Seamless escalation without architectural changes.",
    "compliance.status.done": "Implemented",
    "compliance.status.ready": "Ready",

    "pricing.label": "Pricing",
    "pricing.title": "Transparent and fair",
    "pricing.subtitle": "Start for free, scale as you grow.",
    "pricing.period": "/month",
    "pricing.popular": "Popular",
    "pricing.free.name": "Starter",
    "pricing.free.f1": "5 hours/month",
    "pricing.free.f2": "Up to 5 participants",
    "pricing.free.f3": "10 languages",
    "pricing.free.f4": "Standard support",
    "pricing.free.cta": "Start for free",
    "pricing.pro.name": "Business",
    "pricing.pro.f1": "Unlimited hours",
    "pricing.pro.f2": "Unlimited participants",
    "pricing.pro.f3": "30+ languages",
    "pricing.pro.f4": "API access",
    "pricing.pro.f5": "Priority support",
    "pricing.pro.cta": "Choose Business",
    "pricing.ent.name": "Enterprise",
    "pricing.ent.amount": "Custom",
    "pricing.ent.f1": "Everything in Business",
    "pricing.ent.f2": "High-risk compliance",
    "pricing.ent.f3": "Dedicated infrastructure",
    "pricing.ent.f4": "SLA & onboarding",
    "pricing.ent.f5": "DPA & FRIA support",
    "pricing.ent.cta": "Contact us",

    "cta.title": "Ready for multilingual meetings?",
    "cta.subtitle": "Start now for free — no password, no credit card, no obligation.",
    "cta.placeholder": "your@email.com",
    "cta.button": "Send Magic Link",
    "cta.hint": "We'll send you a sign-in link by email. No password needed.",

    "footer.desc": "Real-time AI interpreting for a connected world. Secure, compliant, European.",
    "footer.product": "Product",
    "footer.docs": "Documentation",
    "footer.api": "API Reference",
    "footer.legal": "Legal",
    "footer.privacy": "Privacy Policy",
    "footer.imprint": "Imprint",
    "footer.terms": "Terms of Service",
    "footer.aup": "Acceptable Use Policy",
    "footer.company": "Company",
    "footer.about": "About us",
    "footer.contact": "Contact",
    "footer.blog": "Blog",
    "footer.rights": "All rights reserved.",
  },

  fr: {
    "nav.features": "Fonctionnalités",
    "nav.how": "Comment ça marche",
    "nav.compliance": "Conformité",
    "nav.pricing": "Tarifs",
    "nav.cta": "Commencer",

    "hero.badge": "Traduction en temps réel par IA",
    "hero.title": "La langue connecte.<br>Nadini traduit.",
    "hero.subtitle": "Interprétation IA en temps réel pour réunions, conférences et communication professionnelle — multilingue, sécurisé, conforme au AI Act.",
    "hero.cta_primary": "Essayer gratuitement",
    "hero.cta_secondary": "Voir la démo",
    "hero.trust": "Plus de 200 entreprises européennes nous font confiance",
    "hero.demo_live": "Live — 120 ms de latence",

    "features.label": "Fonctionnalités",
    "features.title": "Tout ce dont votre communication multilingue a besoin",
    "features.subtitle": "Nadini combine les modèles d'IA les plus avancés avec une infrastructure européenne sécurisée.",
    "features.f1.title": "Traduction en temps réel",
    "features.f1.desc": "Interprétation simultanée avec moins de 200 ms de latence. Parlez pendant que vos participants écoutent dans leur langue.",
    "features.f2.title": "RGPD & AI Act",
    "features.f2.desc": "Entièrement conforme au RGPD et à l'AI Act Art. 50. Transparence, journaux d'audit, souveraineté des données dans l'UE.",
    "features.f3.title": "Participants illimités",
    "features.f3.desc": "Réunions, conférences, webinaires — que ce soit 2 ou 2 000 participants. S'adapte automatiquement à vos besoins.",
    "features.f4.title": "30+ langues",
    "features.f4.desc": "De l'allemand et l'anglais à l'arabe, le mandarin et le japonais. Support linguistique en constante croissance.",
    "features.f5.title": "Connexion sans mot de passe",
    "features.f5.desc": "Connexion par Magic Link par e-mail — aucun mot de passe requis. Sécurisé par JWT RS256, rotation de tokens et verrouillage automatique.",
    "features.f6.title": "API & intégration",
    "features.f6.desc": "API RESTful, streaming WebSocket, endpoint JWKS. Intégrez Nadini facilement dans votre infrastructure existante.",

    "how.label": "Comment ça marche",
    "how.title": "Trois étapes vers des réunions multilingues",
    "how.s1.title": "Connexion par Magic Link",
    "how.s1.desc": "Entrez votre adresse e-mail et cliquez sur le lien dans votre boîte de réception. Pas de mot de passe, pas de complications.",
    "how.s2.title": "Démarrer une réunion",
    "how.s2.desc": "Créez une réunion et invitez des participants. Chacun choisit sa langue préférée.",
    "how.s3.title": "Parler & comprendre",
    "how.s3.desc": "Parlez librement — Nadini traduit en temps réel pour tous les participants. Transcription incluse.",

    "compliance.label": "Confiance & Conformité",
    "compliance.title": "Conçu pour les normes européennes",
    "compliance.subtitle": "Nadini répond aux exigences réglementaires les plus strictes — par conception, pas après coup.",
    "compliance.c1.desc": "Divulgation IA transparente avec textes versionnés, confirmation obligatoire et archivage permanent.",
    "compliance.c2.desc": "Traitement des données dans l'UE. Contrats de sous-traitance, délais de suppression, droits d'audit — tout est réglé.",
    "compliance.c3.title": "Journalisation d'audit",
    "compliance.c3.desc": "Journaux d'audit catégorisés avec conservation configurable. Journaux de conformité permanents, journaux standard basés sur des règles.",
    "compliance.c4.title": "Niveaux de risque hybrides",
    "compliance.c4.desc": "Tenants standard et à haut risque avec des exigences de conformité séparées. Escalade transparente sans changement d'architecture.",
    "compliance.status.done": "Implémenté",
    "compliance.status.ready": "Prêt",

    "pricing.label": "Tarifs",
    "pricing.title": "Transparent et équitable",
    "pricing.subtitle": "Commencez gratuitement, évoluez selon vos besoins.",
    "pricing.period": "/mois",
    "pricing.popular": "Populaire",
    "pricing.free.name": "Starter",
    "pricing.free.f1": "5 heures/mois",
    "pricing.free.f2": "Jusqu'à 5 participants",
    "pricing.free.f3": "10 langues",
    "pricing.free.f4": "Support standard",
    "pricing.free.cta": "Commencer gratuitement",
    "pricing.pro.name": "Business",
    "pricing.pro.f1": "Heures illimitées",
    "pricing.pro.f2": "Participants illimités",
    "pricing.pro.f3": "30+ langues",
    "pricing.pro.f4": "Accès API",
    "pricing.pro.f5": "Support prioritaire",
    "pricing.pro.cta": "Choisir Business",
    "pricing.ent.name": "Enterprise",
    "pricing.ent.amount": "Sur mesure",
    "pricing.ent.f1": "Tout de Business",
    "pricing.ent.f2": "Conformité haut risque",
    "pricing.ent.f3": "Infrastructure dédiée",
    "pricing.ent.f4": "SLA & onboarding",
    "pricing.ent.f5": "AVV & support FRIA",
    "pricing.ent.cta": "Nous contacter",

    "cta.title": "Prêt pour des réunions multilingues ?",
    "cta.subtitle": "Commencez maintenant gratuitement — sans mot de passe, sans carte de crédit, sans engagement.",
    "cta.placeholder": "votre@email.fr",
    "cta.button": "Envoyer le Magic Link",
    "cta.hint": "Nous vous enverrons un lien de connexion par e-mail. Aucun mot de passe requis.",

    "footer.desc": "Interprétation IA en temps réel pour un monde connecté. Sécurisé, conforme, européen.",
    "footer.product": "Produit",
    "footer.docs": "Documentation",
    "footer.api": "Référence API",
    "footer.legal": "Mentions légales",
    "footer.privacy": "Politique de confidentialité",
    "footer.imprint": "Mentions légales",
    "footer.terms": "CGV",
    "footer.aup": "Politique d'utilisation",
    "footer.company": "Entreprise",
    "footer.about": "À propos",
    "footer.contact": "Contact",
    "footer.blog": "Blog",
    "footer.rights": "Tous droits réservés.",
  }
};

const langNames = { de: "Deutsch", en: "English", fr: "Français" };

function setLanguage(lang) {
  if (!translations[lang]) return;

  document.documentElement.lang = lang;

  // Update text content
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    const text = translations[lang][key];
    if (text) el.innerHTML = text;
  });

  // Update placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    const text = translations[lang][key];
    if (text) el.placeholder = text;
  });

  // Update page title
  const titles = {
    de: "Nadini — KI-Dolmetschplattform | nadini.ai",
    en: "Nadini — AI Interpreting Platform | nadini.ai",
    fr: "Nadini — Plateforme d'interprétation IA | nadini.ai"
  };
  document.title = titles[lang] || titles.de;

  // Update active lang button
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });

  // Store preference
  localStorage.setItem("nadini-lang", lang);
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem("nadini-lang");
  const browserLang = navigator.language.slice(0, 2);
  const lang = saved || (translations[browserLang] ? browserLang : "de");
  setLanguage(lang);
});
