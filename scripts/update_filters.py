# Скрипт для обновления фильтров во всех шаблонах тикетов

COMPACT_FILTERS = '''<!-- Фильтры -->
<div class="filters-card card border-0 shadow-sm mb-4">
  <div class="card-body py-3">
    <form method="get" action="{form_action}">
      <div class="row g-2 align-items-end">
        <!-- Статус -->
        <div class="col-md-2">
          <label for="status_id" class="form-label small text-muted mb-1">Статус</label>
          <select name="status_id" id="status_id" class="form-select form-select-sm rounded-1">
            <option value="">Все</option>
            {% for s in statuses %}
              <option value="{{{ s.id }}}" {% if request.query_params.get('status_id')|int == s.id %}selected{% endif %}>
                {{{{ s.name }}}}
              </option>
            {% endfor %}
          </select>
        </div>

        <!-- Категория -->
        <div class="col-md-2">
          <label for="category_id" class="form-label small text-muted mb-1">Категория</label>
          <select name="category_id" id="category_id" class="form-select form-select-sm rounded-1">
            <option value="">Все</option>
            {% for c in categories %}
              <option value="{{{ c.id }}}" {% if request.query_params.get('category_id')|int == c.id %}selected{% endif %}>
                {{{{ c.name }}}}
              </option>
            {% endfor %}
          </select>
        </div>

        <!-- Архив -->
        <div class="col-md-2">
          <label for="archived" class="form-label small text-muted mb-1">Архив</label>
          <select name="archived" id="archived" class="form-select form-select-sm rounded-1">
            <option value="active" {% if archived_filter == "active" %}selected{% endif %}>
              Активные
            </option>
            <option value="archived" {% if archived_filter == "archived" %}selected{% endif %}>
              Архив
            </option>
            <option value="all" {% if archived_filter == "all" %}selected{% endif %}>
              Все
            </option>
          </select>
        </div>

        <!-- Кнопки -->
        <div class="col-md-3 d-flex gap-2">
          <button type="submit" class="btn btn-sm btn-primary rounded-1 px-3">
            🔍
          </button>
          <a href="{reset_url}" class="btn btn-sm btn-outline-secondary rounded-1 px-3">
            ✕
          </a>
        </div>
      </div>

      <!-- Дополнительные настройки -->
      <details class="mt-3">
        <summary class="text-muted small" style="cursor: pointer;">
          ⚙️ Дополнительные настройки
        </summary>
        <div class="row g-2 align-items-end mt-2 pt-3 border-top">
          <div class="col-md-2">
            <label for="sort_by" class="form-label small text-muted mb-1">Сортировка</label>
            <select name="sort_by" id="sort_by" class="form-select form-select-sm rounded-1">
              {% for f in ["id", "track_id", "created_at", "updated_at", "status_id", "priority"] %}
                <option value="{{ f }}" {% if sort_by == f %}selected{% endif %}>
                  {{ f }}
                </option>
              {% endfor %}
            </select>
          </div>

          <div class="col-md-2">
            <div class="form-check mt-4">
              <input
                type="checkbox"
                class="form-check-input"
                name="sort_desc"
                value="true"
                id="sort_desc"
                {% if sort_desc %}checked{% endif %}
              />
              <label class="form-check-label small" for="sort_desc">
                По убыванию
              </label>
            </div>
          </div>

          <div class="col-md-2">
            <label for="limit" class="form-label small text-muted mb-1">Лимит</label>
            <input
              type="number"
              class="form-control form-control-sm rounded-1"
              name="limit"
              id="limit"
              value="{{ limit if limit else '10' }}"
              min="1"
              max="500"
            />
          </div>

          <div class="col-md-2">
            <label for="offset" class="form-label small text-muted mb-1">Смещение</label>
            <input
              type="number"
              class="form-control form-control-sm rounded-1"
              name="offset"
              id="offset"
              value="{{ offset if offset else '0' }}"
              min="0"
            />
          </div>
        </div>
      </details>
    </form>
  </div>
</div>
'''

print("Скрипт для обновления фильтров")
print("Используйте этот шаблон для обновления всех файлов")
