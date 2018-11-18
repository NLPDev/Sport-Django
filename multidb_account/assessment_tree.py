from django.db import connections

from multidb_account.utils import dictfetchall


def _make_recursive_assessment_tree_cte():
    """ Make recursive tree TopCategory->SubCategory->...->Assessment """
    return '''
    WITH RECURSIVE q AS (
          -- Start of the recursion. Top level sub categories
          SELECT sc_top.id AS sc_id,
                 sc_top.id AS top_sc_id, 
                 sc_top.parent_top_category_id AS tc_id, 
                 o.id AS organisation_id,
                 o.own_assessments_only,
                 a.is_public_everywhere,
                 a.is_private
          FROM multidb_account_assessment_sub_category sc_top
          LEFT JOIN multidb_account_assessment a ON a.parent_sub_category_id = sc_top.id
          LEFT JOIN multidb_account_organisation_own_assessments oa ON oa.assessment_id = a.id
          LEFT JOIN multidb_account_organisation o ON o.id = oa.organisation_id
          WHERE sc_top.parent_top_category_id IS NOT NULL
          
        -- Every next child level of subcategories
        UNION ALL
          SELECT sc.id AS sc_id,
                 q.top_sc_id, 
                 q.tc_id, 
                 o.id AS organisation_id,
                 o.own_assessments_only,
                 a.is_public_everywhere,
                 a.is_private
          FROM multidb_account_assessment_sub_category sc
              JOIN q ON sc.parent_sub_category_id = q.sc_id
          LEFT JOIN multidb_account_assessment a ON a.parent_sub_category_id = sc.id
          LEFT JOIN multidb_account_organisation_own_assessments oa ON oa.assessment_id = a.id
          LEFT JOIN multidb_account_organisation o ON o.id = oa.organisation_id
        )
        
        -- Get sub categories from the tree that share the same top level sub category
        SELECT DISTINCT *
        FROM
        (
          SELECT
            q_by_topcat.tc_id AS topcat_id,
            q.sc_id AS subcat_id,
            q_by_topcat.organisation_id,

            -- How many org's private assessments does this sub category have
            SUM(
                CASE WHEN q_by_topcat.organisation_id IN %s AND q_by_topcat.own_assessments_only = TRUE
                THEN 1
                ELSE 0 END
            ) OVER (PARTITION BY q.sc_id) AS our_own_assessments_only_count,
            SUM(
                CASE WHEN q_by_topcat.organisation_id IN %s 
                THEN 1
                ELSE 0 END
            ) OVER (PARTITION BY q.sc_id) AS our_private_count,
            SUM(
                CASE WHEN q_by_topcat.organisation_id NOT IN %s 
                THEN 1
                ELSE 0 END
            ) OVER (PARTITION BY q.sc_id) AS alien_private_count,
            SUM(
                CASE WHEN q.is_public_everywhere 
                THEN 1
                ELSE 0 END
            ) OVER (PARTITION BY q.sc_id) AS public_everywhere_assessments_count,
            SUM(
                CASE 
                WHEN q.is_private OR q.is_private IS NULL THEN 0
                ELSE 1 END
            ) OVER (PARTITION BY q.sc_id) AS public_assessments_count
          FROM q
          JOIN q AS q_by_topcat ON q_by_topcat.top_sc_id = q.top_sc_id
        ) qTop
    '''


def get_assessment_tree_filtered_by_org_own_assessments(localized_db, own_assessments_only_org_ids, our_org_ids):
    with connections[localized_db].cursor() as cursor:
        cte = _make_recursive_assessment_tree_cte()

        # Get only own_assessments_only org assessments
        if own_assessments_only_org_ids:
            sql = cte + 'WHERE our_own_assessments_only_count != 0 ' \
                        'OR public_everywhere_assessments_count != 0;'
            cursor.execute(sql, [tuple(own_assessments_only_org_ids or {0}), tuple(our_org_ids or {0}), (0,)])
            return dictfetchall(cursor)

        # Get only our private and not alien orgs private
        sql = cte + 'WHERE alien_private_count = 0 ' \
                    'OR our_private_count != 0 ' \
                    'OR public_everywhere_assessments_count != 0 ' \
                    'OR public_assessments_count != 0;'
        cursor.execute(sql, [(0,), tuple(our_org_ids or {0}), tuple(our_org_ids or {0})])
        return dictfetchall(cursor)
