#!/usr/bin/env python3
"""
Скрипт для автоматической миграции URL-ов API с v1 на v2
"""

import os
import re
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple


class APIMigrator:
    """
    Класс для автоматической миграции API URL-ов
    """
    
    def __init__(self):
        self.url_mappings = {
            # Profile endpoints
            r'/api/profile/student': '/api/v2/profile/student/',
            r'/api/profile/change_gender': '/api/v2/profile/change-gender/',
            r'/api/profile/QR/toggle': '/api/v2/profile/toggle-qr/',
            r'/api/profile/history/(\d+)': r'/api/v2/profile/history/\1/',
            r'/api/profile/history/by_date': '/api/v2/profile/history/by-date/',
            r'/api/profile/history_with_self/(\d+)': r'/api/v2/profile/history-with-self/\1/',
            
            # Enrollment endpoints
            r'/api/enrollment/enroll': '/api/v2/enrollment/enroll/',
            r'/api/enrollment/unenroll': '/api/v2/enrollment/unenroll/',
            r'/api/enrollment/unenroll_by_trainer': '/api/v2/enrollment/unenroll-by-trainer/',
            
            # Group endpoints
            r'/api/group/(\d+)': r'/api/v2/group/\1/',
            r'/api/select_sport': '/api/v2/group/select-sport/',
            r'/api/sports': '/api/v2/group/sports/',
            
            # Training endpoints
            r'/api/training/(\d+)': r'/api/v2/training/\1/',
            r'/api/training/(\d+)/check_in': r'/api/v2/training/\1/check-in/',
            r'/api/training/(\d+)/cancel_check_in': r'/api/v2/training/\1/cancel-check-in/',
            
            # Attendance endpoints
            r'/api/attendance/suggest_student': '/api/v2/attendance/suggest-student/',
            r'/api/attendance/(\d+)/grades': r'/api/v2/attendance/training/\1/grades/',
            r'/api/attendance/(\d+)/grades\.csv': r'/api/v2/attendance/training/\1/grades.csv',
            r'/api/attendance/(\d+)/report': r'/api/v2/attendance/group/\1/report/',
            r'/api/attendance/mark': '/api/v2/attendance/mark/',
            r'/api/attendance/(\d+)/hours': r'/api/v2/attendance/student/\1/hours/',
            r'/api/attendance/(\d+)/negative_hours': r'/api/v2/attendance/student/\1/negative-hours/',
            r'/api/attendance/(\d+)/better_than': r'/api/v2/attendance/student/\1/better-than/',
            
            # Calendar endpoints
            r'/api/calendar/(-?\d+)/schedule': r'/api/v2/calendar/sport/\1/schedule/',
            r'/api/calendar/trainings': '/api/v2/calendar/trainings/',
            
            # Reference endpoints
            r'/api/reference/upload': '/api/v2/reference/upload/',
            
            # Self sport endpoints
            r'/api/selfsport/upload': '/api/v2/selfsport/upload/',
            r'/api/selfsport/types': '/api/v2/selfsport/types/',
            r'/api/selfsport/strava_parsing': '/api/v2/selfsport/strava-parsing/',
            
            # Fitness test endpoints
            r'/api/fitnesstest/result': '/api/v2/fitnesstest/result/',
            r'/api/fitnesstest/upload': '/api/v2/fitnesstest/upload/',
            r'/api/fitnesstest/upload/(\d+)': r'/api/v2/fitnesstest/upload/\1/',
            r'/api/fitnesstest/exercises': '/api/v2/fitnesstest/exercises/',
            r'/api/fitnesstest/sessions': '/api/v2/fitnesstest/sessions/',
            r'/api/fitnesstest/sessions/(\d+)': r'/api/v2/fitnesstest/sessions/\1/',
            r'/api/fitnesstest/suggest_student': '/api/v2/fitnesstest/suggest-student/',
            
            # Measurement endpoints
            r'/api/measurement/student_measurement': '/api/v2/measurement/student-measurement/',
            r'/api/measurement/get_results': '/api/v2/measurement/results/',
            r'/api/measurement/get_measurements': '/api/v2/measurement/measurements/',
            
            # Semester endpoints
            r'/api/semester': '/api/v2/semester/',
            
            # Analytics endpoints
            r'/api/analytics/attendance': '/api/v2/analytics/attendance/',
            
            # Medical groups endpoints
            r'/api/medical_groups/': '/api/v2/medical_groups/',
        }
        
        self.file_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.html', '.md', '.txt']
        self.stats = {
            'files_processed': 0,
            'files_modified': 0,
            'urls_migrated': 0,
            'errors': []
        }
    
    def migrate_directory(self, directory: str, dry_run: bool = True) -> Dict:
        """
        Мигрирует все файлы в директории
        """
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Migrating directory: {directory}")
        print(f"Looking for files with extensions: {', '.join(self.file_extensions)}")
        
        for file_path in self._find_files(directory_path):
            try:
                self._migrate_file(file_path, dry_run)
            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(f"ERROR: {error_msg}")
        
        return self.stats
    
    def migrate_file(self, file_path: str, dry_run: bool = True) -> Dict:
        """
        Мигрирует отдельный файл
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Migrating file: {file_path}")
        
        try:
            self._migrate_file(file_path, dry_run)
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"ERROR: {error_msg}")
        
        return self.stats
    
    def _find_files(self, directory: Path) -> List[Path]:
        """
        Находит все файлы с нужными расширениями
        """
        files = []
        for ext in self.file_extensions:
            files.extend(directory.rglob(f'*{ext}'))
        return files
    
    def _migrate_file(self, file_path: Path, dry_run: bool):
        """
        Мигрирует отдельный файл
        """
        self.stats['files_processed'] += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Пропускаем бинарные файлы
            return
        
        original_content = content
        changes = []
        
        # Применяем все миграции
        for old_pattern, new_pattern in self.url_mappings.items():
            pattern = re.compile(old_pattern)
            matches = pattern.findall(content)
            
            if matches:
                new_content = pattern.sub(new_pattern, content)
                if new_content != content:
                    changes.append({
                        'pattern': old_pattern,
                        'replacement': new_pattern,
                        'matches': len(matches)
                    })
                    content = new_content
                    self.stats['urls_migrated'] += len(matches)
        
        # Если есть изменения
        if content != original_content:
            self.stats['files_modified'] += 1
            
            if changes:
                print(f"  Modified: {file_path}")
                for change in changes:
                    print(f"    {change['matches']} matches: {change['pattern']} -> {change['replacement']}")
            
            if not dry_run:
                # Создаем бэкап
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Записываем новый контент
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"    Backup created: {backup_path}")
    
    def generate_report(self) -> str:
        """
        Генерирует отчет о миграции
        """
        report = f"""
API Migration Report
===================

Files processed: {self.stats['files_processed']}
Files modified: {self.stats['files_modified']}
URLs migrated: {self.stats['urls_migrated']}
Errors: {len(self.stats['errors'])}

"""
        
        if self.stats['errors']:
            report += "Errors:\n"
            for error in self.stats['errors']:
                report += f"  - {error}\n"
        
        return report
    
    def save_mappings_json(self, output_path: str):
        """
        Сохраняет маппинги URL-ов в JSON файл
        """
        mappings = {}
        for old_pattern, new_pattern in self.url_mappings.items():
            # Упрощаем регулярные выражения для JSON
            simple_old = old_pattern.replace(r'\d+', '{id}').replace(r'-?\d+', '{id}')
            simple_new = new_pattern.replace(r'\1', '{id}')
            mappings[simple_old] = simple_new
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
        
        print(f"URL mappings saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Migrate API URLs from v1 to v2')
    parser.add_argument('path', help='Path to file or directory to migrate')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Perform a dry run without making changes (default)')
    parser.add_argument('--execute', action='store_true', 
                        help='Execute the migration (overrides --dry-run)')
    parser.add_argument('--report', type=str, help='Save migration report to file')
    parser.add_argument('--mappings', type=str, help='Save URL mappings to JSON file')
    
    args = parser.parse_args()
    
    # Определяем режим выполнения
    dry_run = not args.execute
    
    migrator = APIMigrator()
    
    # Сохраняем JSON маппинги если запрошено
    if args.mappings:
        migrator.save_mappings_json(args.mappings)
    
    # Выполняем миграцию
    path = Path(args.path)
    if path.is_file():
        stats = migrator.migrate_file(str(path), dry_run)
    elif path.is_dir():
        stats = migrator.migrate_directory(str(path), dry_run)
    else:
        print(f"ERROR: Path not found: {args.path}")
        return 1
    
    # Выводим отчет
    report = migrator.generate_report()
    print(report)
    
    # Сохраняем отчет в файл если запрошено
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {args.report}")
    
    return 0


if __name__ == '__main__':
    exit(main())
