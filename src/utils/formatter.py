"""
Formatter Module.

This module provides functions to format OSINT results for display.
"""
from typing import Dict, List, Any, Optional
from aiogram.utils.markdown import escape_md, quote_html


def extract_images_from_result(result: Dict[str, Any]) -> List[str]:
    """
    Extract image URLs from OSINT search result.
    
    Args:
        result: OSINT search result
        
    Returns:
        List of unique image URLs found
    """
    images = set()
    result_type = result.get('type', '')
    
    # Extract from different result types
    if result_type == 'username':
        analyses = result.get('analyses', [])
        for analysis in analyses:
            data = analysis.get('data', {})
            # Look for image fields
            for key in ['profile_image', 'avatar', 'picture', 'photo', 'image']:
                if key in data and data[key]:
                    img_url = data[key]
                    # Validate URL
                    if isinstance(img_url, str) and (img_url.startswith('http://') or img_url.startswith('https://')):
                        images.add(img_url)
    
    elif result_type in ['phone', 'email']:
        results_list = result.get('results', [])
        for item in results_list:
            data = item.get('data', {})
            for key in ['profile_image', 'avatar', 'picture', 'photo', 'image']:
                if key in data and data[key]:
                    img_url = data[key]
                    if isinstance(img_url, str) and (img_url.startswith('http://') or img_url.startswith('https://')):
                        images.add(img_url)
    
    return list(images)


def format_result(result: Dict[str, Any]) -> str:
    """
    Format OSINT results for display in Telegram.
    
    Args:
        result: Dictionary containing OSINT results
        
    Returns:
        Formatted string for display
    """
    result_type = result.get('type', 'unknown')
    
    # Add cache indicator if present
    output = ""
    if result.get('from_cache'):
        output = "💾 <i>(Из кэша)</i>\n\n"
    
    if result_type == 'username':
        output += format_username_detailed(result)
    elif result_type == 'phone':
        output += format_phone_results(result)
    elif result_type == 'email':
        output += format_email_results(result)
    elif result_type == 'domain_analysis':
        output += format_domain_analysis(result)
    else:
        output += format_generic_result(result)
    
    return output


def format_username_detailed(result: Dict[str, Any]) -> str:
    """Format detailed username search results."""
    query = result.get('query', '')
    analyses = result.get('analyses', [])
    
    if not analyses:
        return f"❌ Результатов не найдено для пользователя: <code>{query}</code>"
    
    lines = [
        f"🔍 <b>Результаты поиска: @{query}</b>\n",
    ]
    
    found_any = False
    for analysis in analyses:
        if not analysis.get('found'):
            platform = analysis.get('platform', 'Unknown')
            lines.append(f"❌ <b>{platform}:</b> Не найдено\n")
        else:
            found_any = True
            platform = analysis.get('platform', 'Unknown')
            url = analysis.get('url', '#')
            data = analysis.get('data', {})
            
            lines.append(f"✅ <b>{platform}:</b>")
            lines.append(f"   🔗 <a href='{url}'>Профиль</a>")
            
            # Show extracted data with fallback to '-'
            if data:
                for key, value in data.items():
                    if key != 'note':
                        key_name = key.replace('_', ' ').title()
                        if value:
                            # Trim long values
                            value_str = str(value)[:200]
                            lines.append(f"   • <b>{key_name}:</b> {value_str}")
                        else:
                            lines.append(f"   • <b>{key_name}:</b> -")
            else:
                lines.append("   • <b>Информация:</b> -")
            
            lines.append("")
    
    if not found_any:
        return f"❌ Результатов не найдено для пользователя: <code>{query}</code>"
    
    lines.append("<i>ℹ️ Данные получены из публичной информации профилей. Да, без хакинга профилей ;)</i>")
    
    return "\n".join(lines)


def format_phone_results(result: Dict[str, Any]) -> str:
    """Format phone search results."""
    query = result.get('query', '')
    results_list = result.get('results', [])
    total_checked = result.get('total_checked', 0)
    
    if not results_list:
        return f"❌ Результатов не найдено для номера: <code>{query}</code>"
    
    lines = [
        f"📱 <b>Поиск по номеру телефона:</b> <code>{query}</code>\n",
        f"<b>Проверено платформ:</b> {total_checked}\n",
    ]
    
    found_count = sum(1 for r in results_list if r.get('status') == 'found')
    lines.append(f"<b>Найдено упоминаний:</b> {found_count}\n")
    
    for item in results_list:
        if item.get('status') == 'found':
            platform = item.get('platform', 'Unknown')
            url = item.get('url', '#')
            
            lines.append(f"✅ <b>{platform}</b>")
            lines.append(f"   🔗 <a href='{url}'>Проверить</a>")
            
            # Show any data found
            data = item.get('data', {})
            has_data = False
            for key, value in data.items():
                if key != 'phone':  # Skip redundant phone field
                    has_data = True
                    key_name = key.replace('_', ' ').title()
                    value_str = str(value) if value else '-'
                    lines.append(f"   • <b>{key_name}:</b> {value_str}")
            
            if not has_data:
                lines.append(f"   • <b>Статус:</b> Номер найден в системе")
            
            lines.append("")
    
    lines.append("<i>⚠️ Номер телефона может быть привязан к одному или нескольким аккаунтам.</i>")
    
    return "\n".join(lines)


def format_email_results(result: Dict[str, Any]) -> str:
    """Format email search results."""
    query = result.get('query', '')
    email_domain = result.get('email_domain', '')
    results_list = result.get('results', [])
    
    if not results_list:
        return f"❌ Результатов не найдено для email: <code>{query}</code>"
    
    lines = [
        f"📧 <b>Поиск по email:</b> <code>{query}</code>\n",
        f"<b>Домен:</b> <code>{email_domain}</code>\n",
    ]
    
    # Group results by status
    accessible = [r for r in results_list if r.get('status') == 'accessible']
    not_found = [r for r in results_list if r.get('status') == 'not_found']
    errors = [r for r in results_list if r.get('status') == 'error']
    
    if accessible:
        lines.append(f"✅ <b>Найдено на {len(accessible)} платформах:</b>\n")
        for item in accessible:
            platform = item.get('platform', 'Unknown')
            url = item.get('url', '#')
            lines.append(f"   • <a href='{url}'>{platform}</a>")
        lines.append("")
    
    if not_found:
        lines.append(f"❌ <b>Не найдено на {len(not_found)} платформах</b>\n")
    
    lines.append("<i>ℹ️ Email может быть связана с одним или несколькими аккаунтами.</i>")
    
    return "\n".join(lines)


def format_domain_analysis(result: Dict[str, Any]) -> str:
    """Format domain analysis results."""
    query = result.get('query', '')
    analyses = result.get('analyses', [])
    
    if not analyses:
        return f"❌ Результатов анализа не найдено для: <code>{query}</code>"
    
    lines = [
        f"🌍 <b>Анализ домена:</b> <code>{query}</code>\n",
    ]
    
    for analysis in analyses:
        analysis_type = analysis.get('type', '')
        data = analysis.get('data', {})
        
        # Пропускаем пустые анализы
        if not data:
            continue
        
        if analysis_type == 'domain':
            lines.append("<b>📋 Основная информация:</b>")
        elif analysis_type == 'dns_info':
            lines.append("<b>🔗 DNS информация:</b>")
        else:
            continue  # Пропускаем неизвестные типы
        
        has_data = False
        for key, value in data.items():
            if key != 'error' and key != 'type':
                has_data = True
                key_name = key.replace('_', ' ').title()
                
                if isinstance(value, list):
                    value_str = ', '.join(str(v) for v in value) if value else '-'
                elif value is None or value == '':
                    value_str = '-'
                else:
                    value_str = str(value)
                
                lines.append(f"   • <b>{key_name}:</b> <code>{value_str}</code>")
        
        if has_data:
            lines.append("")
    
    lines.append("<i>ℹ️ Информация о домене получена из общедоступных источников.</i>")
    
    return "\n".join(lines)


def format_generic_result(result: Dict[str, Any]) -> str:
    """Format generic results."""
    query = result.get('query', '')
    results_list = result.get('results', [])
    
    if not results_list:
        return f"❌ Результатов не найдено для: <code>{query}</code>"
    
    lines = [
        f"🔍 <b>Результаты поиска:</b> <code>{query}</code>\n",
    ]
    
    for item in results_list:
        platform = item.get('platform', 'Unknown')
        status = item.get('status', 'unknown')
        url = item.get('url', '#')
        
        if status == 'found' or item.get('valid'):
            lines.append(f"✅ <a href='{url}'><b>{platform}</b></a>")
        else:
            lines.append(f"❌ <b>{platform}</b> - не найдено")
    
    return "\n".join(lines)


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters."""
    return escape_md(text)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return quote_html(text)