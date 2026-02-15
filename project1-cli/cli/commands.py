"""CLI команды для файлового менеджера"""
import click
import sys
import os
import json


@click.group()
def cli():
    """Файловый менеджер с дополнительными функциями"""
    pass


# ===== КОМАНДА 1: COPY =====
@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('destination', type=click.Path())
def copy(source, destination):
    """
    Копирует файл

    Пример: python -m cli.commands copy test.txt backup/test.txt
    """
    try:
        from core.file_manager import copy_file

        result = copy_file(source, destination)
        click.echo(f"✅ Файл скопирован: {source} → {result}")

    except Exception as e:
        click.echo(f"❌ Ошибка при копировании: {e}", err=True)
        sys.exit(1)


# ===== КОМАНДА 2: SEARCH =====
@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.argument('pattern')
def search(directory, pattern):
    """
    Ищет файлы по паттерну в директории (рекурсивно)

    Пример: python -m cli.commands search ./documents "квитанция"
    Пример: python -m cli.commands search . "*.pdf"
    """
    try:
        from core.file_manager import search_files

        results = search_files(directory, pattern)

        if results:
            click.echo(f"✅ Найдено файлов: {len(results)}\n")
            for i, file_path in enumerate(results, 1):
                click.echo(f"{i}. {file_path}")
        else:
            click.echo(f"⚠️  Файлы не найдены по паттерну: {pattern}")

    except Exception as e:
        click.echo(f"❌ Ошибка при поиске: {e}", err=True)
        sys.exit(1)


# ===== КОМАНДА 3: ANALYZE =====
@cli.command()
@click.argument('directory', type=click.Path(exists=True))
def analyze(directory):
    """
    Анализирует размер директории и её содержимого

    Пример: python -m cli.commands analyze ./documents
    """
    try:
        from core.file_manager import analyze_directory

        info = analyze_directory(directory)

        click.echo(f"\n📊 АНАЛИЗ ДИРЕКТОРИИ: {os.path.abspath(directory)}")
        click.echo("=" * 70)
        click.echo(f"📁 Всего файлов: {info['total_files']}")
        click.echo(f"💾 Общий размер: {info['size_mb']} MB ({info['size_gb']} GB)")

        if info['breakdown']:
            click.echo(f"\n🔝 Топ элементов по размеру:")
            click.echo("-" * 70)

            for i, item in enumerate(info['breakdown'][:10], 1):
                icon = "📄" if item['type'] == 'file' else "📁"
                name = item['name']
                size = item['size_mb']

                # Добавить количество файлов для папок
                if item['type'] == 'directory':
                    files_info = f" ({item['files']} файлов)"
                else:
                    files_info = ""

                click.echo(f"{i:2d}. {icon} {name:30s} {size:8.2f} MB{files_info}")

    except Exception as e:
        click.echo(f"❌ Ошибка при анализе: {e}", err=True)
        sys.exit(1)


# ===== БОНУС: ГЕНЕРАТОР КВИТАНЦИЙ =====
@cli.command()
@click.argument('student_name')
@click.argument('contract_number')
@click.argument('month_year')
@click.argument('amount', type=float)
@click.option('-c', '--course', 'courses', multiple=True, required=True,
              help='Предмет (можно указать несколько раз)')
@click.option('--compensation', default='', help='Компенсация')
@click.option('-o', '--output', default='receipt_output.pdf', help='Путь для сохранения')
def generate_receipt_cmd(student_name, contract_number, month_year, amount,
                         courses, compensation, output):
    """
    Генерирует квитанцию ПД-5

    Пример:
    python -m cli.commands generate-receipt-cmd "Иванов Иван" "8БТ-1" "Апрель" 8000
           -c "Математика" -c "Физика" -o receipt.pdf
    """
    try:
        # ИЗМЕНЕН ИМПОРТ
        from core.receipt import generate_receipt

        result = generate_receipt(
            student_name=student_name,
            courses=list(courses),
            contract_number=contract_number,
            month_year=month_year,
            amount=amount,
            compensation=compensation,
            output_path=output
        )

        click.echo(f"✅ Квитанция создана: {result}")

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Ошибка при генерации квитанции: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('-o', '--output', default='receipt_output.pdf', help='Путь для сохранения')
def generate_from_json(json_file, output):
    """
    Генерирует квитанцию из JSON файла

    Пример: python -m cli.commands generate-from-json student.json -o receipt.pdf
    """
    try:
        # ИЗМЕНЕН ИМПОРТ
        from core.receipt import generate_receipt_from_dict

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        result = generate_receipt_from_dict(data, output)
        click.echo(f"✅ Квитанция создана: {result}")

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except json.JSONDecodeError:
        click.echo(f"❌ Некорректный JSON файл: {json_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
