# Common Data Transformation Patterns

This reference contains reusable code patterns for common data transformations.

## Pattern 1: Chinese Category → English Labels

### R
```r
df %>% mutate(
  new_var = case_when(
    var == "北京" ~ "Beijing",
    var == "上海" ~ "Shanghai",
    var == "广州" ~ "Guangzhou",
    TRUE ~ as.character(var)
  )
)
```

### Python
```python
df['new_var'] = df['var'].map({
    '北京': 'Beijing',
    '上海': 'Shanghai',
    '广州': 'Guangzhou'
}).fillna(df['var'])
```

---

## Pattern 2: Chinese Yes/No → Binary

### R
```r
df %>% mutate(
  binary_var = ifelse(var == "是", 1, 0),
  yes_pct = mean(var == "是", na.rm = TRUE) * 100
)
```

### Python
```python
df['binary_var'] = df['var'].apply(lambda x: 1 if x == '是' else 0)
df['yes_pct'] = (df['var'] == '是').mean() * 100
```

---

## Pattern 3: String Date → Age Calculation

### R
```r
df %>% mutate(
  year = substr(date_col, 1, 4),
  age = 2024 - as.numeric(year),
  age_group = cut(age,
                   breaks = c(0, 25, 35, 45, 100),
                   labels = c("20-25", "26-35", "36-45", "46+"))
)
```

### Python
```python
df['year'] = df['date_col'].str[:4].astype(int)
df['age'] = 2024 - df['year']
df['age_group'] = pd.cut(df['age'],
                          bins=[0, 25, 35, 45, 100],
                          labels=['20-25', '26-35', '36-45', '46+'])
```

---

## Pattern 4: Multi-Select (String → Binary)

### Data Structure
- Empty string `""` = not selected
- Non-empty string = selected

### R
```r
df %>% mutate(
  selected = ifelse(var != "", 1, 0)
)
```

### Python
```python
df['selected'] = df['var'].apply(lambda x: 1 if x != "" else 0)
```

---

## Pattern 5: Likert Scale (1-5) → Mean Score

### Data Structure
```r
"完全不影响" = 1
"比较不影响" = 2
"一般" = 3
"比较影响" = 4
"非常影响" = 5
```

### R
```r
df %>% mutate(
  score_num = case_when(
    response == "完全不影响" ~ 1,
    response == "比较不影响" ~ 2,
    response == "一般" ~ 3,
    response == "比较影响" ~ 4,
    response == "非常影响" ~ 5
  )
) %>%
  group_by(category) %>%
  summarise(
    mean_score = mean(score_num, na.rm = TRUE),
    sd_score = sd(score_num, na.rm = TRUE)
  )
```

### Python
```python
score_map = {
    '完全不影响': 1,
    '比较不影响': 2,
    '一般': 3,
    '比较影响': 4,
    '非常影响': 5
}
df['score_num'] = df['response'].map(score_map)

result = df.groupby('category')['score_num'].agg(['mean', 'std'])
```

---

## Pattern 6: Percentage Calculation

### R
```r
df %>%
  group_by(category) %>%
  mutate(
    count = n(),
    percentage = n / sum(n) * 100
  ) %>%
  ungroup()
```

### Python
```python
df['percentage'] = df.groupby('category')['category'].transform('count') / len(df) * 100
```

---

## Pattern 7: Standardization (Z-score)

### R
```r
df %>% mutate(
  z_score = (var - mean(var, na.rm = TRUE)) / sd(var, na.rm = TRUE)
)
```

### Python
```python
df['z_score'] = (df['var'] - df['var'].mean()) / df['var'].std()
```

---

## Pattern 8: Filtering with Multiple Conditions

### R
```r
df %>%
  filter(!is.na(var1)) %>%
  filter(var2 == "target_value") %>%
  filter(var3 >= threshold)
```

### Python
```python
df = df[
    (df['var1'].notna()) &
    (df['var2'] == 'target_value') &
    (df['var3'] >= threshold)
]
```

---

## Pattern 9: Long to Wide Format

### R
```r
df %>%
  pivot_wider(names_from = category_var,
              values_from = value_var)
```

### Python
```python
df.pivot(index='id', columns='category_var', values='value_var')
```

---

## Pattern 10: Wide to Long Format

### R
```r
df %>%
  pivot_longer(cols = c(var1, var2, var3),
               names_to = "category",
               values_to = "value")
```

### Python
```python
df.melt(id_vars=['id'], value_vars=['var1', 'var2', 'var3'],
        var_name='category', value_name='value')
```
