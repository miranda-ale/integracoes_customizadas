"use strict";

function applyQuestaoLinkPreviewOverride() {
	if (!frappe.ui || !frappe.ui.LinkPreview) {
		return false;
	}

	const proto = frappe.ui.LinkPreview.prototype;
	if (!proto || proto.__questao_preview_patched) {
		return true;
	}

	const PREVIEW_HTML_LABEL = "Previa";
	const PREVIEW_TEXT_LABEL = "Previa Texto";

	proto.get_content_html = function (preview_data) {
		let content_html = "";
		const preview_html = preview_data[PREVIEW_HTML_LABEL];
		const has_preview_html =
			typeof preview_html === "string" && preview_html.includes("questao-preview");

		Object.keys(preview_data).forEach((key) => {
			if (["preview_image", "preview_title", "name"].includes(key)) {
				return;
			}
			if (has_preview_html && key === PREVIEW_TEXT_LABEL) {
				return;
			}

			let value = preview_data[key] ?? "";
			const is_preview_html = has_preview_html && key === PREVIEW_HTML_LABEL;
			if (!is_preview_html) {
				value = frappe.ellipsis(value, 280);
			}

			content_html += `
				<div class="preview-field${is_preview_html ? " preview-field-html" : ""}">
					<div class="preview-label text-muted">${__(key)}</div>
					<div class="preview-value${is_preview_html ? " preview-value-html" : ""}">${value}</div>
				</div>
			`;
		});

		return `<div class="preview-table">${content_html}</div>`;
	};

	proto.__questao_preview_patched = true;
	return true;
}

if (!applyQuestaoLinkPreviewOverride()) {
	frappe.ready(() => {
		if (!applyQuestaoLinkPreviewOverride()) {
			frappe.after_ajax(() => {
				applyQuestaoLinkPreviewOverride();
			});
		}
	});
}
