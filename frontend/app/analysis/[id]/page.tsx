import AnalysisPageClient from './_client';

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let initialData: any = null;
  try {
    const res = await fetch(`http://127.0.0.1:8001/api/meetings/${id}/results`, {
      cache: 'no-store',
    });
    if (res.ok) initialData = await res.json();
  } catch { /* ignore — client will fetch & poll */ }
  return <AnalysisPageClient initialData={initialData} />;
}
