import graphene
from crm.schema import Query as CRMQuery, Mutation as CRMMutation


class Query(CRMQuery, graphene.ObjectType):
    """
    Root query combining all CRM queries
    """
    pass


class Mutation(CRMMutation, graphene.ObjectType):
    """
    Root mutation combining all CRM mutations
    """
    pass


# Create the main schema
schema = graphene.Schema(
    query=Query,
    mutation=Mutation
)