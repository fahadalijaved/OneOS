package com.fahadali.oneos.core.model

/** The broker authorizes UIDs, so shared-UID packages must be presented together. */
object GuestRootPermissions {
    data class Grant(val packageName: String, val uid: Int, val allowed: Boolean)
    data class App(val packageName: String, val uid: Int, val allowed: Boolean, val label: String, val system: Boolean)
    data class Group(val uid: Int, val apps: List<App>) {
        val primary get() = apps.first()
        val allowed get() = apps.any { it.allowed }
        val system get() = apps.all { it.system }
    }
    enum class Access { ALL, ALLOWED, DENIED }
    enum class Kind { USER, ALL, SYSTEM }
    fun parse(text: String): List<Grant> = text.lineSequence().mapNotNull { line ->
        val p=line.trim().split(Regex("\\s+"));if(p.size!=3) return@mapNotNull null
        val uid=p[1].toIntOrNull() ?: return@mapNotNull null
        if(uid<10000 || !p[0].matches(Regex("[A-Za-z][A-Za-z0-9_.]{0,254}")) || p[2] !in setOf("0","1")) return@mapNotNull null
        Grant(p[0],uid,p[2]=="1")
    }.distinctBy { it.packageName }.toList()
    fun groups(apps: List<App>): List<Group> = apps.groupBy { it.uid }.map { (uid,rows) ->
        Group(uid,rows.sortedWith(compareBy<App> { it.system }.thenBy(String.CASE_INSENSITIVE_ORDER) { it.label }.thenBy { it.packageName }))
    }.sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { g: Group -> g.primary.label }.thenBy { it.uid })
    fun filter(groups: List<Group>, query: String, access: Access, kind: Kind): List<Group> {
        val terms=query.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        return groups.filter { group ->
            (access==Access.ALL || group.allowed==(access==Access.ALLOWED)) &&
                (kind==Kind.ALL || group.system==(kind==Kind.SYSTEM)) &&
                terms.all { term -> group.uid.toString().contains(term) || group.apps.any { it.label.contains(term,true) || it.packageName.contains(term,true) } }
        }
    }
}
