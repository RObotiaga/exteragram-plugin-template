-keep class ru.n08i40k.template.** {
    *;
}

# kotlinx-coroutines-core 1.10.2 ships R8 consumer rules which preserve volatile
# fields accessed through AtomicReferenceFieldUpdater. The embedded Kotlin and
# coroutines classes are relocated under template_shaded before R8 sees them, so
# the upstream package names no longer match. Keep the same semantics after
# relocation instead of copying the now-stale META-INF consumer rule verbatim.
# Re-audit these translated rules whenever kotlinx-coroutines-core is upgraded.
-keepclassmembers class ru.n08i40k.template_shaded.kotlinx.coroutines.** {
    volatile <fields>;
}

# Kotlin SafeContinuation is embedded and relocated as well; upstream coroutines
# explicitly preserves its volatile fields for the same AtomicFU-style access.
-keepclassmembers class ru.n08i40k.template_shaded.kotlin.coroutines.SafeContinuation {
    volatile <fields>;
}

-dontobfuscate

# Keep metadata which can be observed at runtime, but deliberately drop
# RuntimeInvisibleAnnotations. Compile-only markers such as AndroidX @AnyThread,
# JetBrains annotations and animal-sniffer annotations have CLASS retention and
# must not become runtime dependencies of the standalone in-memory DEX.
-keepattributes RuntimeVisibleAnnotations,RuntimeVisibleParameterAnnotations,AnnotationDefault,InnerClasses,EnclosingMethod,Signature
