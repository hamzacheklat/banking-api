Voici une explication claire et concrète de **toutes les alertes**, comme si tu étais en production avec une API réelle.
Je te détaille pour chacune :

* ce que ça détecte
* pourquoi c’est important
* quand ça déclenche
* quoi faire quand elle s’active

---

# 🚨 Explication des alertes Prometheus

---

# 1) `APIInstanceDown`

```yaml
expr: up == 0
for: 1m
severity: critical
```

## Ce que ça signifie

Prometheus n’arrive plus à contacter l’API.

* Le process est mort
* Le container est crashé
* Le serveur est down
* Le réseau est cassé

## Quand ça déclenche

Si l’API ne répond plus pendant **1 minute**.

## Gravité

🔴 **CRITICAL**
C’est une panne directe.

## Action à faire

1. Vérifier le service :

   ```
   systemctl status
   docker ps
   ```
2. Vérifier les logs
3. Redémarrer le service si nécessaire

---

# 2) `HighErrorRate`

```yaml
expr:
  sum(rate(http_requests_5xx_total[5m]))
  /
  sum(rate(http_requests_total[5m]))
  > 0.05
for: 2m
severity: critical
```

## Ce que ça signifie

Plus de **5% des requêtes retournent des erreurs 5xx**.

Exemple :

* 1000 requêtes/min
* 60 erreurs/min
  → 6% d’erreurs → alerte

## Quand ça déclenche

Si le taux d’erreur reste >5% pendant **2 minutes**.

## Gravité

🔴 **CRITICAL**
Ça veut dire que les utilisateurs subissent des erreurs.

## Causes possibles

* Base de données down
* Service externe cassé
* Bug déployé en prod
* Timeout massif

## Action à faire

1. Vérifier logs d’erreurs
2. Vérifier DB / services externes
3. Rollback si nécessaire

---

# 3) `ErrorSpike`

```yaml
expr: sum(rate(http_requests_5xx_total[1m])) > 5
for: 1m
severity: warning
```

## Ce que ça signifie

Plus de **5 erreurs par seconde**.

## Différence avec HighErrorRate

| Alerte        | Type                  |
| ------------- | --------------------- |
| HighErrorRate | % d’erreurs           |
| ErrorSpike    | volume brut d’erreurs |

## Quand ça déclenche

Si plus de 5 erreurs/sec pendant 1 minute.

## Gravité

🟡 **WARNING**

## Action

* Surveiller la situation
* Vérifier les logs

---

# 4) `HighLatencyP95`

```yaml
p95 > 1s
for: 3m
severity: warning
```

## Ce que ça signifie

95% des requêtes prennent **plus d’1 seconde**.

### Exemple

Sur 100 requêtes :

* 95 requêtes >1s
* seulement 5 rapides

→ expérience utilisateur dégradée

## Quand ça déclenche

Si p95 >1s pendant 3 minutes.

## Gravité

🟡 **WARNING**

## Causes possibles

* Base de données lente
* CPU saturé
* Trop de requêtes
* Service externe lent

## Action

1. Regarder les endpoints lents
2. Vérifier CPU / DB
3. Regarder les requêtes les plus longues

---

# 5) `CriticalLatencyP99`

```yaml
p99 > 3s
for: 2m
severity: critical
```

## Ce que ça signifie

1% des requêtes prennent plus de **3 secondes**.

Ça veut dire :

* certaines requêtes sont **très lentes**
* souvent des timeouts ou blocages

## Quand ça déclenche

Si p99 >3s pendant 2 minutes.

## Gravité

🔴 **CRITICAL**

## Causes fréquentes

* Deadlock DB
* API externe en timeout
* Thread bloqué
* Fuite mémoire

## Action

1. Identifier l’endpoint lent
2. Vérifier logs timeout
3. Vérifier ressources

---

# 6) `HighMemoryUsage`

```yaml
process_resident_memory_bytes > 1GB
for: 5m
severity: warning
```

## Ce que ça signifie

Le process utilise plus de **1 Go de RAM**.

## Quand ça déclenche

Si mémoire >1 Go pendant 5 minutes.

## Gravité

🟡 **WARNING**

## Causes possibles

* Fuite mémoire
* Trop de requêtes en parallèle
* Cache trop gros
* Mauvais usage de la DB

## Action

1. Vérifier l’évolution mémoire dans Grafana
2. Redémarrer le service si nécessaire
3. Chercher fuite mémoire

---

# 7) `HighCPUUsage`

```yaml
rate(process_cpu_seconds_total[1m]) > 0.8
for: 5m
severity: warning
```

## Ce que ça signifie

Le process utilise **plus de 80% CPU**.

## Quand ça déclenche

Si CPU >80% pendant 5 minutes.

## Gravité

🟡 **WARNING**

## Causes possibles

* Boucle infinie
* Trop de trafic
* Traitement lourd
* Worker bloqué

## Action

1. Vérifier CPU dans Grafana
2. Vérifier endpoints actifs
3. Augmenter nombre de workers si nécessaire

---

# Résumé rapide (tableau)

| Alerte             | Ce que ça veut dire        | Gravité     |
| ------------------ | -------------------------- | ----------- |
| APIInstanceDown    | API inaccessible           | 🔴 Critical |
| HighErrorRate      | >5% erreurs                | 🔴 Critical |
| ErrorSpike         | pic d’erreurs              | 🟡 Warning  |
| HighLatencyP95     | API lente pour la majorité | 🟡 Warning  |
| CriticalLatencyP99 | requêtes très lentes       | 🔴 Critical |
| HighMemoryUsage    | trop de RAM                | 🟡 Warning  |
| HighCPUUsage       | CPU saturé                 | 🟡 Warning  |

---

# Ordre de gravité réel en production

1. 🔴 APIInstanceDown
2. 🔴 HighErrorRate
3. 🔴 CriticalLatencyP99
4. 🟡 HighLatencyP95
5. 🟡 ErrorSpike
6. 🟡 HighMemoryUsage
7. 🟡 HighCPUUsage

---

Si tu veux, je peux te fournir :

* une **stratégie d’alerting SRE complète** (warning vs critical par endpoint)
* des **alerts spécifiques à ton job Cinego**
* un **dashboard d’investigation** pour diagnostiquer une alerte en 30 secondes.
