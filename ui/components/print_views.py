from __future__ import annotations

import html

import streamlit.components.v1 as components


def render_print_shell(title: str, subtitle_lines: list[str], headers: list[str], rows_html: str, button_text: str, fn_name: str) -> None:
    subtitle_html = "".join(f"<div style='font-size:13px;color:#475467;margin-top:4px;'>{html.escape(line)}</div>" for line in subtitle_lines if line)
    headers_html = "".join(f"<th style='padding:8px 10px;background:#f8fafc;'>{html.escape(header)}</th>" for header in headers)
    printable_body = f"""
    <div style='border:2px solid #98a2b3;border-radius:14px;padding:18px 20px;background:#ffffff;'>
        <div style='text-align:center;font-size:28px;font-weight:900;letter-spacing:1px;'>{html.escape(title)}</div>
        <div style='margin-top:14px;'>{subtitle_html}</div>
        <table style='width:100%;border-collapse:collapse;margin-top:18px;font-size:14px;' border='1'>
            <thead><tr>{headers_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """
    printable_html = f"""
    <script>
    function {fn_name}() {{
        const printWindow = window.open('', '_blank');
        printWindow.document.write(document.getElementById('print-shell-content').innerHTML);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
    }}
    </script>
    <div style='display:flex;flex-direction:column;gap:12px;padding:20px;font-family:Arial,Microsoft YaHei,sans-serif;color:#101828;'>
        <button onclick='{fn_name}()' style='align-self:flex-start;padding:8px 16px;'>{html.escape(button_text)}</button>
        <div style='border:1px solid #d0d5dd;border-radius:14px;background:#f8fafc;padding:16px;overflow:auto;max-height:900px;'>
            <div style='transform:scale(0.8);transform-origin:top left;width:125%;'>
                <div id='print-shell-content'>{printable_body}</div>
            </div>
        </div>
    </div>
    """
    components.html(printable_html, height=980)
